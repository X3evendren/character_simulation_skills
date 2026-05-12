/** Generation Controller — Turn-level interrupt orchestration.
 *  Core state machine: idle → generating → aborting → idle.
 */
import type { Span, SpanOp, GenStatus, RepackContext, ToolResult } from "./types";
import { ContextRepacker, detectIntent, type RepackParams } from "./context-repacker";
import { InflightSummarizer } from "./inflight-summarizer";

export interface SpanRenderer {
  apply(op: SpanOp): void;
  freeze(): void;
  getFluidSpans(): Span[];
  getStableSpans(): Span[];
  getLockedSpans(): Span[];
}

export interface SpanBasedGenerator {
  generate(
    systemPrompt: string,
    userMessage: string,
    signal: AbortSignal,
  ): AsyncGenerator<SpanOp>;
}

export interface ControllerAgent {
  getCommittedSpans(): Span[];
  snapshot: { formatForPrompt(): string; freeze(...args: any[]): string; markDirty(): void };
  psychologyEngine: { analyze(...args: any[]): Promise<any> };
  selfModel: { formatCapabilities(): string; formatForHotPath(): string };
  affectiveResidue: { formatForPrompt(): string };
  temporalHorizon: { formatForPrompt(): string };
  driveSublimator: { buildAttentionBias(drives: any): string };
  drives: any;
  groundTruth: any;
  config: { name: string; traits: string; essence?: string; rules?: string };
  /** Run Cold Path — called when generation completes. Returns psychology result. */
  runColdPath(turnCtx: any): Promise<any>;
  /** Consume stale Slow results from aborted turns */
  consumeStaleSlow(staleResults: any[]): void;
}

const UNSAFE_TOOLS = new Set(["write_file", "edit_file", "exec_command", "web_fetch"]);

export class GenerationController {
  status: GenStatus = "idle";
  private abortController: AbortController | null = null;
  private spanRenderer: SpanRenderer;
  private contextRepacker: ContextRepacker;
  private inflightSummarizer: InflightSummarizer;
  private spanGenerator: SpanBasedGenerator | null = null;
  private agent: ControllerAgent;

  private queuedTurn: string | null = null;
  private queuedToolResults: ToolResult[] = [];
  private staleSlowResults: any[] = [];
  private lastColdPathResult: any = null;
  private runningTools = new Set<string>(); // currently executing tool names
  private inflightSummary = "";

  constructor(
    spanRenderer: SpanRenderer,
    inflightSummarizer: InflightSummarizer,
    agent: ControllerAgent,
  ) {
    this.spanRenderer = spanRenderer;
    this.contextRepacker = new ContextRepacker();
    this.inflightSummarizer = inflightSummarizer;
    this.agent = agent;
  }

  setGenerator(gen: SpanBasedGenerator): void {
    this.spanGenerator = gen;
  }

  // ═══════════════════════════════════════
  // Public API
  // ═══════════════════════════════════════

  /** Called when user presses Enter with new input. */
  async handleTurn(input: string): Promise<void> {
    if (this.status === "generating") {
      if (this._hasUnsafeToolRunning()) {
        this.queuedTurn = input;
        return;
      }
      await this._abort();
    }

    if (this.status === "aborting") {
      this.queuedTurn = input;
      return;
    }

    await this._startTurn(input);
  }

  /** Called when a tool execution completes. */
  onToolComplete(result: ToolResult): void {
    this.runningTools.delete(result.name);
    this.queuedToolResults.push(result);

    // If a turn was queued waiting for unsafe tool, process it now
    if (this.queuedTurn && !this._hasUnsafeToolRunning() && this.status === "idle") {
      const next = this.queuedTurn;
      this.queuedTurn = null;
      this.handleTurn(next);
    }
  }

  /** Called when a tool execution starts. */
  onToolStart(toolName: string): void {
    this.runningTools.add(toolName);
  }

  /** Called when Slow (soft-aborted) completes in background. */
  onSlowComplete(result: any): void {
    this.staleSlowResults.push(result);
  }

  /** Initialize with a completed Cold Path result (e.g., from agent initialization). */
  setLastColdPathResult(result: any): void {
    this.lastColdPathResult = result;
  }

  // ═══════════════════════════════════════
  // Internal
  // ═══════════════════════════════════════

  private async _abort(): Promise<void> {
    this.status = "aborting";

    // Fast Track: immediate HTTP cancel
    this.abortController?.abort();
    this.abortController = null;

    // Summarize inflight fluid text
    const fluidSpans = this.spanRenderer.getFluidSpans();
    this.inflightSummary = await this.inflightSummarizer.summarize(fluidSpans);

    // Freeze renderer — clear FLUID, keep STABLE+LOCKED
    this.spanRenderer.freeze();

    this.status = "idle";
  }

  private async _startTurn(input: string): Promise<void> {
    if (!this.spanGenerator) {
      throw new Error("SpanBasedGenerator not set. Call setGenerator() first.");
    }

    this.status = "generating";
    this.abortController = new AbortController();

    // Detect intent
    const intentState = detectIntent(input);
    const taskMode = intentState.constraints.includes("task_mode");

    // Get committed spans from renderer
    const stableSpans = this.spanRenderer.getStableSpans();
    const lockedSpans = this.spanRenderer.getLockedSpans();
    const committedSpans = [...lockedSpans, ...stableSpans];

    // Memory snapshot
    const memorySnapshot = this.agent.snapshot.formatForPrompt();

    // Build repack params
    const repackParams: RepackParams = {
      committedSpans,
      inflightSummary: this.inflightSummary,
      userInput: input,
      memorySnapshot,
      psychologyState: this.lastColdPathResult,
      toolResults: [...this.queuedToolResults],
      intentState,
      characterConfig: this.agent.config,
      capabilities: this.agent.selfModel.formatCapabilities(),
      groundTruthText: "", // populated below if groundTruth exists
      affectiveResidueText: this.agent.affectiveResidue.formatForPrompt(),
      driveBiasText: this.agent.driveSublimator.buildAttentionBias(this.agent.drives),
      selfNarrativeText: this.agent.selfModel.formatForHotPath(),
      temporalHorizonText: this.agent.temporalHorizon.formatForPrompt(),
      taskMode,
    };

    // GroundTruth
    if (this.agent.groundTruth) {
      const { formatGroundTruthForPrompt } = await import("../character/state/ground-truth");
      repackParams.groundTruthText = formatGroundTruthForPrompt(this.agent.groundTruth);
    }

    // Repack context + build prompt
    const ctx = this.contextRepacker.repack(repackParams);
    const systemPrompt = this.contextRepacker.buildPrompt(ctx, repackParams);
    const userMessage = taskMode
      ? `【用户输入 — 任务模式，请简洁准确】\n${input}`
      : `【用户输入】\n${input}`;

    // Generate
    try {
      for await (const spanOp of this.spanGenerator.generate(
        systemPrompt, userMessage, this.abortController.signal,
      )) {
        if (this.abortController.signal.aborted) break;
        this.spanRenderer.apply(spanOp);
      }
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        // Re-throw non-abort errors for the caller to handle
        throw err;
      }
    }

    // Cleanup
    this.status = "idle";
    this.queuedToolResults = [];
    this.inflightSummary = "";
    this.abortController = null;

    // Run Cold Path — captures the psychology result for next turn's repack
    this.lastColdPathResult = await this.agent.runColdPath({ input, response: "" });

    // Consume stale Slow results (from aborted turns)
    if (this.staleSlowResults.length > 0) {
      this.agent.consumeStaleSlow(this.staleSlowResults);
      this.staleSlowResults = [];
    }

    // Process queued turn
    if (this.queuedTurn) {
      const next = this.queuedTurn;
      this.queuedTurn = null;
      // Use setTimeout to avoid stack overflow from recursive handleTurn
      setImmediate(() => this.handleTurn(next));
    }
  }

  private _hasUnsafeToolRunning(): boolean {
    for (const name of this.runningTools) {
      if (UNSAFE_TOOLS.has(name)) return true;
    }
    return false;
  }
}
