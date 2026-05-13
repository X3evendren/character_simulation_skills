/**
 * Character Agent — Main orchestrator ties all character subsystems together.
 * This is the master entry point that ties all character subsystems together.
 */
import { MindState } from "../mind/state";
import { PsychologyEngine, PsychologyResult } from "../mind/psychology";
import { UnifiedParams } from "../mind/params";
import { ParamsModulator } from "../mind/params-modulator";
import { DriveState } from "../mind/drives";
import { DriveDynamics } from "../mind/dynamics";
import { DriveSublimator } from "../mind/sublimator";
import { SaturationState, ContinuousParams } from "../mind/saturation";
import { SaturationDetector } from "../mind/relational";
import { SelfModel } from "../mind/self-model";
import { AffectiveResidue } from "../mind/emotion";
import { TemporalHorizon } from "../mind/horizon";
import { PredictionTracker } from "../mind/prediction";
import { PostFilter } from "../guard/post-filter";
import { WorkingMemory } from "../memory/working";
import { ShortTermMemory } from "../memory/short-term";
import { LongTermMemory } from "../memory/long-term";
import { CoreGraphMemory } from "../memory/core-graph";
import { ArchiveMemory } from "../memory/archive";
import { SleepCycleMetabolism } from "../memory/metabolism";
import { FrozenSnapshot } from "../memory/snapshot";
import { FeedbackLoop } from "../learn/feedback-loop";
import { SelfReflection } from "../learn/self-reflection";
import { SkillLibrary } from "../learn/skill-library";
import { loadAssistantConfig, loadMemoryConfig, ensureSkillsDir } from "./config-loader";
import { buildSystemPrompt, buildUserPrompt } from "./prompt";
import { SpanBasedGenerator } from "./dual-track";
import { createGroundTruth, type GroundTruth } from "../mind/ground-truth";
import { ToolRegistry } from "../tools/registry";
import { registerAllTools } from "../tools/register-all";
import type { Tracer, Span } from "../telemetry";
import { GuardPipeline, createRegexDenyGate, createSafetyCheckGate, createToolArgsValidatorGate } from "../guard";
import { CheckpointManager, type RootState, type DerivedState } from "../recovery";
export interface AgentHook {
  beforeAnalyze?(ctx: TurnContext): Promise<void>;
  afterAnalyze?(ctx: TurnContext, r: PsychologyResult): Promise<void>;
  beforeModulate?(ctx: TurnContext): Promise<void>;
  beforeBuild?(ctx: TurnContext): Promise<void>;
  onStream?(ctx: TurnContext, delta: string): Promise<void>;
  afterGenerate?(ctx: TurnContext): Promise<void>;
  beforeRespond?(ctx: TurnContext): Promise<void>;
}

export interface TurnContext {
  input: string;
  systemPrompt: string;
  response: string;
  psychology?: PsychologyResult;
  behaviorModes: Record<string, number>;
  toolResults: any[];
  totalTokens: number;
  elapsedMs: number;
}

export class CharacterAgent {
  // Subsystems
  mindState: MindState;
  params: UnifiedParams;
  modulator: ParamsModulator;
  drives: DriveState;
  dynamics: DriveDynamics;
  driveSublimator: DriveSublimator;
  saturation: SaturationState;
  continuousParams: ContinuousParams;
  saturationDetector: SaturationDetector;
  selfModel: SelfModel;
  affectiveResidue: AffectiveResidue;
  temporalHorizon: TemporalHorizon;
  toolRegistry: ToolRegistry;
  predictionTracker: PredictionTracker;
  postFilter: PostFilter;
  workingMemory: WorkingMemory;
  shortTermMemory: ShortTermMemory;
  longTermMemory: LongTermMemory;
  coreGraph: CoreGraphMemory;
  archiveMemory: ArchiveMemory;
  metabolism: SleepCycleMetabolism;
  snapshot: FrozenSnapshot;
  feedbackLoop: FeedbackLoop;
  selfReflection: SelfReflection;
  skillLibrary: SkillLibrary;

  // LLM providers
  fastProvider: any;
  slowProvider: any;
  psychologyEngine: PsychologyEngine;

  // Observability
  tracer?: Tracer;

  // Guardrails
  guardPipeline: GuardPipeline;

  // Recovery
  checkpointManager?: CheckpointManager;

  // Eval
  evalMode = false;

  // Hooks
  hooks: AgentHook[] = [];

  // Config
  config: ReturnType<typeof loadAssistantConfig>;
  memConfig: ReturnType<typeof loadMemoryConfig>;

  // State
  tickCount = 0;
  turnCount = 0;
  initialized = false;
  private firstTurnDone = false;

  /** Shared factual state — Hot Path reads, all writes via tool results */
  groundTruth: GroundTruth = createGroundTruth();

  constructor(opts: {
    configDir: string;
    genProvider: any;
    psychProvider: any;
    genModel?: string;
    psychModel?: string;
    fastProvider?: any;
    tracer?: Tracer;
    guardPipeline?: GuardPipeline;
    checkpointManager?: CheckpointManager;
    evalMode?: boolean;
  }) {
    // Config
    this.config = loadAssistantConfig(opts.configDir);
    this.memConfig = loadMemoryConfig(opts.configDir);

    // Mind
    this.mindState = new MindState();

    // Params
    this.params = new UnifiedParams();
    this.modulator = new ParamsModulator(this.params);

    // Drive
    this.drives = new DriveState();
    this.dynamics = new DriveDynamics();
    this.driveSublimator = new DriveSublimator();

    // Saturation
    this.saturation = new SaturationState();
    this.continuousParams = new ContinuousParams(this.saturation);
    this.saturationDetector = new SaturationDetector();

    // Consciousness
    this.selfModel = new SelfModel();
    this.selfModel.initFromConfig(this.config as unknown as Record<string, string>);
    this.affectiveResidue = new AffectiveResidue();
    this.temporalHorizon = new TemporalHorizon();
    this.toolRegistry = new ToolRegistry();
    registerAllTools(this.toolRegistry);
    this.predictionTracker = new PredictionTracker();

    // Anti-RLHF
    this.postFilter = new PostFilter();

    // Memory
    this.workingMemory = new WorkingMemory(this.memConfig.workingMemorySize);
    this.shortTermMemory = new ShortTermMemory(":memory:", this.memConfig.shortTermMemorySize);
    this.longTermMemory = new LongTermMemory(":memory:", this.memConfig.longTermMemorySize);
    this.coreGraph = new CoreGraphMemory(":memory:", this.memConfig.coreGraphMaxNodes, this.memConfig.coreGraphMaxEdges);
    this.archiveMemory = new ArchiveMemory(":memory:");
    this.metabolism = new SleepCycleMetabolism(this.workingMemory, this.shortTermMemory, this.longTermMemory, this.coreGraph, this.archiveMemory, this.skillLibrary);
    this.snapshot = new FrozenSnapshot();

    // Learning
    this.feedbackLoop = new FeedbackLoop();
    this.selfReflection = new SelfReflection();
    this.skillLibrary = new SkillLibrary(ensureSkillsDir(opts.configDir));

    // LLM
    this.fastProvider = opts.fastProvider ?? opts.genProvider;
    this.slowProvider = opts.genProvider;
    this.psychologyEngine = new PsychologyEngine(opts.psychProvider, opts.psychModel ?? "");

    // Observability
    this.tracer = opts.tracer;

    // Guardrails — use provided pipeline or create default
    this.guardPipeline = opts.guardPipeline ?? new GuardPipeline([
      createRegexDenyGate(),
      createSafetyCheckGate(),
      createToolArgsValidatorGate(),
    ]);
    this.toolRegistry.guardPipeline = this.guardPipeline;

    // Recovery
    this.checkpointManager = opts.checkpointManager;

    // Eval
    this.evalMode = opts.evalMode ?? false;
  }

  async initialize(): Promise<void> {
    this.skillLibrary.loadFromDisk();
    await this.workingMemory.initialize();
    await this.shortTermMemory.initialize();
    await this.longTermMemory.initialize();
    await this.coreGraph.initialize();
    await this.archiveMemory.initialize();
    this.initialized = true;
  }

  async run(input: string, onDelta?: (delta: string) => Promise<void>): Promise<TurnContext> {
    if (!this.initialized) await this.initialize();

    const startTime = Date.now();
    const ctx: TurnContext = {
      input, systemPrompt: "", response: "",
      behaviorModes: {}, toolResults: [], totalTokens: 0, elapsedMs: 0,
    };
    const taskMode = detectTaskMode(input);
    const turnSpan = this.tracer?.startTurn(input);

    this.tickCount++;
    this.turnCount++;

    // Guardrail: check input before processing
    const inputCheck = await this.guardPipeline.checkInput(input);
    if (!inputCheck.allowed) {
      ctx.response = "(输入被安全护栏拦截)";
      ctx.elapsedMs = Date.now() - startTime;
      if (turnSpan) { turnSpan.setStatus("error"); this.tracer?.endSpan(turnSpan); }
      return ctx;
    }

    // Temporal horizon — retention from last turn enters awareness
    this.temporalHorizon.onTurnStart();

    // ═══════════════════════════════════════════
    // HOT PATH — Generation only
    // ═══════════════════════════════════════════

    // Restore memory snapshot
    if (this.snapshot.isStale()) {
      const stmRecords = await this.shortTermMemory.recall(input, 3);
      const ltmRecords = await this.longTermMemory.recall(input, 5);
      const coreSummary = (await this.coreGraph.recall(input, 1))[0]?.content ?? "";
      this.snapshot.freeze({}, ltmRecords, stmRecords, coreSummary);
    }

    // Lightweight emotion analysis (Hot Path — only dominant emotion, not full XML)
    let emoDominant = "neutral";
    let emoIntensity = 0.5;
    const psychSpan = this.tracer?.startSpan("chat", {
      "gen_ai.request.model": this.psychologyEngine.model || "psych-model",
      "gen_ai.operation.name": "psychology_analyze",
    });
    try {
      const lightPsych = await this.psychologyEngine.analyze(
        { description: input, type: taskMode ? "tool_use" : "social", significance: 0.5 },
        this.snapshot.formatForPrompt(), this.mindState, this.drives.toDict(), this.config as unknown as Record<string, string>,
        this.affectiveResidue.vector,
      );
      ctx.psychology = lightPsych; // stored for Cold Path use later
      emoDominant = lightPsych.emotion.dominant;
      emoIntensity = lightPsych.emotion.intensity;
      psychSpan?.setAttribute("emotion.dominant", emoDominant);
      psychSpan?.setAttribute("emotion.intensity", emoIntensity);
    } catch { psychSpan?.setStatus("error"); }
    if (psychSpan) this.tracer?.endSpan(psychSpan);

    // Fast Track param modulation — emotional tone only
    const fastShifts = this.modulator.modulateFast(ctx.psychology ?? undefined);
    this.modulator.applyShifts(fastShifts);

    // Build system prompt (Hot Path — capabilities + groundTruth + taskMode)
    ctx.systemPrompt = buildSystemPrompt({
      config: this.config,
      mindstate: this.mindState,
      capabilities: this.selfModel.formatCapabilities(),
      groundTruth: this.groundTruth,
      snapshot: this.snapshot,
      feedbackLoop: this.feedbackLoop,
      skillLibrary: this.skillLibrary,
      currentInput: input,
      taskMode,
      emotionDominant: emoDominant,
      emotionIntensity: emoIntensity,
      affectiveResidueText: this.affectiveResidue.formatForPrompt(),
      driveBiasText: this.driveSublimator.buildAttentionBias(this.drives),
      selfNarrativeText: this.selfModel.formatForHotPath(),
      temporalHorizonText: this.temporalHorizon.formatForPrompt(),
      isFirstTurn: !this.firstTurnDone,
    });
    this.firstTurnDone = true;

    const userPrompt = buildUserPrompt(input, taskMode);

    // Phase 4: Draft (Fast) + Refine (Slow) + Commit — shared GroundTruth
    for (const h of this.hooks) { await h.beforeBuild?.(ctx); }

    const dualTrack = new SpanBasedGenerator(this.fastProvider, this.slowProvider, this.toolRegistry);
    const responseParts: string[] = [];
    const abortController = new AbortController();

    // Dynamic generation params: saturation + drive style hints
    const hints = this.driveSublimator.buildStyleHints(this.drives);
    const genTemp = Math.max(0.1, Math.min(1.5,
      this.continuousParams.responseTemperature + hints.temperatureShift));
    const genMaxTokens = Math.round(
      this.continuousParams.verbosity * 500 + hints.maxTokensShift);
    for await (const op of dualTrack.generate(ctx.systemPrompt, userPrompt, abortController.signal, this.toolRegistry.getDefinitions(), genTemp, genMaxTokens)) {
      if (op.type === "invalidate") {
        responseParts.length = 0;
        continue;
      }
      const text = op.type === "append" ? op.span.text
        : op.type === "patch" ? op.newText
        : "";
      if (text) {
        responseParts.push(text);
        if (onDelta) await onDelta(text);
        for (const h of this.hooks) { await h.onStream?.(ctx, text); }
      }
    }
    ctx.response = responseParts.join("");

    // Anti-RLHF post-filter (backward compatible)
    const [filtered, modifications] = this.postFilter.replace(ctx.response);
    if (modifications.length > 0) ctx.response = filtered;

    // Guardrail: check output through pipeline
    const outputCheck = await this.guardPipeline.checkOutput(ctx.response);
    ctx.response = outputCheck.content;

    for (const h of this.hooks) { await h.afterGenerate?.(ctx); }

    // Cold Path delegation
    await this.runColdPath({ input, response: ctx.response, psychology: ctx.psychology });

    // Checkpoint: save state at turn boundary
    if (this.checkpointManager) {
      this.checkpointManager.recordUserMessage(input);
      this.checkpointManager.recordAssistantMessage(ctx.response.slice(0, 500));
      this.saveCheckpoint(ctx.systemPrompt);
    }

    ctx.elapsedMs = Date.now() - startTime;
    if (turnSpan) this.tracer?.endTurn(turnSpan, ctx.totalTokens, this.turnCount);
    return ctx;
  }

  /** Cold Path only — post-generation cognition. Called by GenerationController after span-based generation. */
  async runColdPath(params: { input: string; response: string; psychology?: PsychologyResult }): Promise<PsychologyResult> {
    const cpSpan = this.tracer?.startSpan("cold_path", {});
    const { input, response, psychology: existingPsych } = params;

    // Full psychology analysis (Cold Path — this is where psych belongs)
    let psychology = existingPsych ?? null;
    if (!psychology) {
      try {
        psychology = await this.psychologyEngine.analyze(
          { description: input, type: "social", significance: 0.5 },
          this.snapshot.formatForPrompt(), this.mindState, this.drives.toDict(), this.config as unknown as Record<string, string>,
          this.affectiveResidue.vector,
        );
      } catch { psychology = null; }
    }

    if (psychology) {
      const emo = psychology.emotion;
      const fastShifts: Record<string, number> = {};

      // Drives update
      if (emo.pleasure > 0.3) this.drives.applyReward("user_praise", 0.5, input);
      else if (emo.dominant === "sadness") this.drives.applyReward("error", -0.3, input);

      // Saturation + Love Engine
      this.saturation.positiveInteraction(emo.intensity);
      const cp = this.continuousParams;
      this.saturationDetector.observe(1 - cp.precisionSafety, cp.precisionSelfUpdateFromUser);
      const satMode = this.saturationDetector.evaluate();

      // Saturation tracking
      if (satMode === "saturated") {
        this.saturation.deepConnection();
      }

      // Slow Track baseline modulation
      const slowShifts = this.modulator.modulateSlow(psychology, "", fastShifts, this.selfModel.formatForPrompt());
      this.modulator.applyShifts(slowShifts, true);
    }

    // State evolution
    const emoKey = psychology?.emotion?.dominant ?? "neutral";
    const emoVal = psychology?.emotion?.intensity ?? 0.5;

    this.mindState = this.dynamics.step(this.mindState, this.drives,
      psychology?.mindstate ?? { affect: { pleasure: 0, arousal: 0.5, dominance: 0 } });
    this.predictionTracker.observe(this.mindState);
    this.drives.tick(1);
    this.params.decayAllActivations();

    // Memory storage
    const { createMemoryRecord } = await import("../memory/store");
    await this.workingMemory.store(createMemoryRecord({
      content: input, eventType: "user_input", significance: 0.5,
      emotionalSignature: { [emoKey]: emoVal }, tags: ["user", emoKey],
      memoryType: "episodic", confidence: 0.8,
    }));
    await this.workingMemory.store(createMemoryRecord({
      content: response, eventType: "assistant_response", significance: 0.5,
      emotionalSignature: { [emoKey]: emoVal }, tags: ["assistant", emoKey],
      memoryType: "episodic", confidence: 0.7,
    }));
    this.snapshot.markDirty();

    // Memory metabolism
    if (this.metabolism.shouldDaydream(this.tickCount, this.memConfig.daydreamIntervalTicks))
      await this.metabolism.daydream();
    if (this.metabolism.shouldQuickSleep(this.tickCount, this.memConfig.quickSleepIntervalTicks))
      await this.metabolism.quickSleep();

    // Self-reflection
    this.selfReflection.fastReflect(input, response, psychology ?? undefined);
    if (this.selfReflection.shouldSlowReflect(this.turnCount)) {
      const srSpan = this.tracer?.startSpan("chat", {
        "gen_ai.operation.name": "self_reflection",
      });
      await this.selfReflection.slowReflect(this.slowProvider, this.selfModel, this.skillLibrary);
      if (srSpan) this.tracer?.endSpan(srSpan);
    }

    // Affective Residue deposit — passive emotional sediment
    if (psychology) {
      const sig = Math.max(0.2, psychology.emotion.intensity);
      this.affectiveResidue.deposit(
        { dominant: psychology.emotion.dominant, intensity: psychology.emotion.intensity, pleasure: psychology.emotion.pleasure },
        sig,
      );
      // SelfModel narrative update — psych → natural language self-story
      // Update user model from psychology
      if (psychology.emotion.pleasure > 0.3) this.selfModel.updateTrust(+0.02);
      else if (psychology.emotion.pleasure < -0.2) this.selfModel.updateTrust(-0.01);
      this.selfModel.recordInteraction(input, response);
      // Temporal horizon — set retention for next turn
      this.temporalHorizon.onTurnEnd(
        { dominant: psychology.emotion.dominant, intensity: psychology.emotion.intensity },
        false,
      );
    }

    // Save checkpoint at turn boundary (covers Ink TUI path that doesn't go through run())
    if (this.checkpointManager) {
      this.checkpointManager.recordUserMessage(input);
      this.checkpointManager.recordAssistantMessage(response.slice(0, 500));
      this.saveCheckpoint(response.slice(0, 500));
    }

    if (cpSpan) this.tracer?.endSpan(cpSpan);
    return psychology ?? new PsychologyResult();
  }

  /** Consume stale Slow results from aborted turns — feed to memory and self-reflection. */
  consumeStaleSlow(results: any[]): void {
    for (const r of results) {
      if (r?.content) {
        this.selfReflection.fastReflect("(stale slow)", r.content.slice(0, 200), undefined);
      }
    }
  }

  /** Build a RootState snapshot from current agent state. */
  buildRootState(lastSystemPrompt: string): RootState {
    return {
      systemPrompt: lastSystemPrompt,
      memorySnapshot: this.snapshot.formatForPrompt(),
      groundTruthFacts: [...this.groundTruth.facts],
      conversationHistory: [], // populated by checkpoint manager
    };
  }

  /** Build DerivedState from current agent state. */
  buildDerivedState(): DerivedState {
    return {
      affectiveResidue: { ...this.affectiveResidue.vector },
      selfNarrative: `${this.selfModel.relationship.trust.toFixed(2)}`,
      lastEmotion: "neutral",
      saturation: this.saturation.s,
      turnCount: this.turnCount,
    };
  }

  /** Save a checkpoint after a completed turn. */
  saveCheckpoint(systemPrompt: string): void {
    if (!this.checkpointManager) return;
    this.checkpointManager.recordUserMessage(systemPrompt.slice(-500)); // last user context
    this.checkpointManager.save(
      this.buildRootState(systemPrompt),
      this.buildDerivedState(),
    );
  }

  /** Restore agent state from checkpoint data. */
  restoreFromCheckpoint(data: { root: { memorySnapshot: string; groundTruthFacts: string[]; conversationHistory: Array<{role:string;content:string}> }; derived: { affectiveResidue: {warmth:number;weight:number;clarity:number;tension:number}; selfNarrative: string; saturation: number; turnCount: number } }): void {
    // Restore ground truth facts
    this.groundTruth.facts = [...data.root.groundTruthFacts];

    // Restore affective residue
    this.affectiveResidue.vector = { ...data.derived.affectiveResidue };

    // Restore relationship trust
    if (data.derived.selfNarrative) {
      const trust = parseFloat(data.derived.selfNarrative);
      if (!isNaN(trust)) this.selfModel.relationship.trust = trust;
    }

    // Restore saturation
    this.saturation.s = data.derived.saturation;

    // Restore turn count
    this.turnCount = data.derived.turnCount;
    this.firstTurnDone = data.derived.turnCount > 0;

    // Feed conversation history into working memory for context
    for (const msg of data.root.conversationHistory.slice(-10)) {
      this.workingMemory.store({
        recordId: `rec_${Date.now()}_${Math.random()}`,
        content: msg.content.slice(0, 200),
        emotionalSignature: {},
        significance: 0.5,
        eventType: msg.role === "user" ? "user_input" : "assistant_response",
        tags: [msg.role],
        timestamp: Date.now() / 1000 - 1,
        trust: 0.7,
        recallCount: 0,
        memoryType: "episodic",
        confidence: 0.6,
        superseded: false,
        supersededBy: null,
        metadata: {},
      });
    }
  }

  async shutdown(): Promise<void> {
    await this.metabolism.fullSleep();
    await this.workingMemory.shutdown();
    await this.shortTermMemory.shutdown();
    await this.longTermMemory.shutdown();
    await this.coreGraph.shutdown();
  }
}

/** Task keywords: reading files, executing commands, searching, summarizing */
const TASK_KEYWORDS = [
  "读", "打开", "查看", "显示", "列出", "搜索", "找", "查找",
  "执行", "运行", "总结", "概括", "分析", "修改", "编辑", "写",
  "read", "open", "cat", "ls", "find", "grep", "run", "exec",
];

function detectTaskMode(input: string): boolean {
  if (!input) return false;
  const lower = input.toLowerCase();
  return TASK_KEYWORDS.some(kw => lower.includes(kw));
}
