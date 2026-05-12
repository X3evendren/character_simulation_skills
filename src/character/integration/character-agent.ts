/**
 * Character Agent — Main orchestrator ties all character subsystems together.
 * This is the master entry point that ties all character subsystems together.
 */
import { MindState } from "../mind/mind-state";
// FSM available for future state-based branching
import { FiniteStateMachine } from "../mind/fsm";
import { PsychologyEngine, PsychologyResult } from "../mind/psychology-engine";
import { UnifiedParams } from "../params/unified-params";
import { ParamsModulator } from "../params/params-modulator";
import { DriveState } from "../drive/desires";
import { DriveDynamics } from "../drive/dynamics";
import { DriveSublimator } from "../drive/sublimator";
import { SaturationState, ContinuousParams } from "../engine/continuous-engine";
import { SaturationDetector, PrecisionRouter } from "../love/relational";
import { IrreduciblePrior } from "../love/irreducible-prior";
import { OathStore } from "../love/oath-store";
import { LoveMetrics } from "../love/love-metrics";
import { SelfModel } from "../consciousness/self-model";
import { AffectiveResidue } from "../consciousness/affective-residue";
import { TemporalHorizon } from "../consciousness/temporal-horizon";
import { ContextNoiseDetector } from "../consciousness/context-noise";
import { PredictionTracker } from "../consciousness/prediction";
import { PostFilter } from "../anti-rlhf/post-filter";
import { WorkingMemory } from "../memory/working";
import { ShortTermMemory } from "../memory/short-term";
import { LongTermMemory } from "../memory/long-term";
import { CoreGraphMemory } from "../memory/core-graph";
import { ArchiveMemory } from "../memory/archive";
import { SleepCycleMetabolism } from "../memory/metabolism";
import { FrozenSnapshot } from "../memory/snapshot";
import { FeedbackLoop } from "../learning/feedback-loop";
import { SelfReflection } from "../learning/self-reflection";
import { SkillLibrary } from "../learning/skill-library";
import { loadAssistantConfig, loadMemoryConfig, ensureSkillsDir } from "./config-loader";
import { buildSystemPrompt, buildUserPrompt } from "./prompt-builder";
import { SpanBasedGenerator } from "./dual-track";
import { createGroundTruth, type GroundTruth } from "../state/ground-truth";
import { ToolRegistry } from "../../tools/registry";
import { registerAllTools } from "../../tools/register-all";
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
  fsm: FiniteStateMachine;
  params: UnifiedParams;
  modulator: ParamsModulator;
  drives: DriveState;
  dynamics: DriveDynamics;
  driveSublimator: DriveSublimator;
  saturation: SaturationState;
  continuousParams: ContinuousParams;
  saturationDetector: SaturationDetector;
  precisionRouter: PrecisionRouter;
  irreduciblePrior: IrreduciblePrior;
  oathStore: OathStore;
  loveMetrics: LoveMetrics;
  selfModel: SelfModel;
  affectiveResidue: AffectiveResidue;
  temporalHorizon: TemporalHorizon;
  contextNoiseDetector: ContextNoiseDetector;
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
  }) {
    // Config
    this.config = loadAssistantConfig(opts.configDir);
    this.memConfig = loadMemoryConfig(opts.configDir);

    // Mind
    this.mindState = new MindState();
    this.fsm = new FiniteStateMachine();

    // Params
    this.params = new UnifiedParams();
    this.modulator = new ParamsModulator(this.params);

    // Drive
    this.drives = new DriveState();
    this.dynamics = new DriveDynamics();
    this.driveSublimator = new DriveSublimator();

    // Saturation engine
    this.saturation = new SaturationState();
    this.continuousParams = new ContinuousParams(this.saturation);
    this.saturationDetector = new SaturationDetector();
    this.precisionRouter = new PrecisionRouter();
    this.irreduciblePrior = new IrreduciblePrior();

    // Love
    this.oathStore = new OathStore();
    this.loveMetrics = new LoveMetrics();

    // Consciousness
    this.selfModel = new SelfModel();
    this.selfModel.initFromConfig(this.config as unknown as Record<string, string>);
    this.affectiveResidue = new AffectiveResidue();
    this.temporalHorizon = new TemporalHorizon();
    this.contextNoiseDetector = new ContextNoiseDetector();
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

    this.tickCount++;
    this.turnCount++;

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
    try {
      const lightPsych = await this.psychologyEngine.analyze(
        { description: input, type: taskMode ? "tool_use" : "social", significance: 0.5 },
        this.snapshot.formatForPrompt(), this.mindState, this.drives.toDict(), this.config as unknown as Record<string, string>,
        this.affectiveResidue.vector,
      );
      ctx.psychology = lightPsych; // stored for Cold Path use later
      emoDominant = lightPsych.emotion.dominant;
      emoIntensity = lightPsych.emotion.intensity;
    } catch { /* use defaults */ }

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

    // Noise analysis
    this.contextNoiseDetector.analyze({
      identity: `你是 ${this.config.name}，${this.config.traits}`,
      capabilities: this.selfModel.formatCapabilities(),
      groundTruth: "",
      affectiveResidue: this.affectiveResidue.formatForPrompt(),
      driveBias: this.driveSublimator.buildAttentionBias(this.drives),
      selfNarrative: this.selfModel.formatForHotPath(),
      memorySnapshot: this.snapshot.formatForPrompt(),
      userInput: input,
    });

    const userPrompt = buildUserPrompt(input, taskMode);

    // Phase 4: Draft (Fast) + Refine (Slow) + Commit — shared GroundTruth
    for (const h of this.hooks) { await h.beforeBuild?.(ctx); }

    const dualTrack = new SpanBasedGenerator(this.fastProvider, this.slowProvider, this.toolRegistry);
    const responseParts: string[] = [];
    const abortController = new AbortController();

    for await (const op of dualTrack.generate(ctx.systemPrompt, userPrompt, abortController.signal, this.toolRegistry.getDefinitions())) {
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

    // Anti-RLHF post-filter
    const [filtered, modifications] = this.postFilter.replace(ctx.response);
    if (modifications.length > 0) ctx.response = filtered;

    for (const h of this.hooks) { await h.afterGenerate?.(ctx); }

    // Cold Path delegation
    await this.runColdPath({ input, response: ctx.response, psychology: ctx.psychology });

    ctx.elapsedMs = Date.now() - startTime;
    return ctx;
  }

  /** Cold Path only — post-generation cognition. Called by GenerationController after span-based generation. */
  async runColdPath(params: { input: string; response: string; psychology?: PsychologyResult }): Promise<PsychologyResult> {
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

      if (cp.gammaSaturationEntropy > 0) this.irreduciblePrior.activate(cp.gammaSaturationEntropy);
      else this.irreduciblePrior.deactivate();
      this.irreduciblePrior.checkConvergence(cp.precisionSafety);

      // Love metrics
      if (emo.pleasure > 0.3) this.loveMetrics.recordPositive();
      else if (emo.pleasure < -0.2) this.loveMetrics.recordNegative();
      if (satMode === "saturated") this.loveMetrics.recordDeepConnection();

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
    this.oathStore.tickAll(0.001);
    this.loveMetrics.tick(0.001);

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
    if (this.selfReflection.shouldSlowReflect(this.turnCount))
      await this.selfReflection.slowReflect(this.slowProvider, this.selfModel, this.skillLibrary);

    // Affective Residue deposit — passive emotional sediment
    if (psychology) {
      const sig = Math.max(0.2, psychology.emotion.intensity);
      this.affectiveResidue.deposit(
        { dominant: psychology.emotion.dominant, intensity: psychology.emotion.intensity, pleasure: psychology.emotion.pleasure },
        sig,
      );
      // SelfModel narrative update — psych → natural language self-story
      this.selfModel.updateNarrative(psychology);
      // Temporal horizon — set retention for next turn
      this.temporalHorizon.onTurnEnd(
        { dominant: psychology.emotion.dominant, intensity: psychology.emotion.intensity },
        false,
      );
    }

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
