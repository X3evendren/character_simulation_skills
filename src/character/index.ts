/** Character Mind v3 — Unified export barrel. */

// Love Engine
export { Oath, OathStore, OathType, OathState } from "./love/oath-store";
export type { OathConstraint, OathEvent } from "./love/oath-store";
export { IrreduciblePrior } from "./love/irreducible-prior";
export { SaturationDetector, PrecisionRouter, RelationMode } from "./love/relational";
export { RepairEngine, RepairPhase, RepairResult } from "./love/repair-engine";
export { LoveMetrics } from "./love/love-metrics";

// Params
export { UnifiedParams, Param, ChangeSpeed } from "./params/unified-params";
export { ParamsModulator } from "./params/params-modulator";
export type { ModulationRecord } from "./params/params-modulator";

// Engine
export { SaturationState, ContinuousParams, detectBehaviorMode } from "./engine/continuous-engine";

// Mind
export { MindState } from "./mind/mind-state";
export { FiniteStateMachine, State } from "./mind/fsm";
export type { FSMContext } from "./mind/fsm";
export { PsychologyEngine, PsychologyResult, EmotionResult } from "./mind/psychology-engine";
export { extractJSON, extractXML, extractXMLAttr } from "./mind/json-parser";

// Drive
export { DriveState, createDesire } from "./drive/desires";
export { DriveDynamics, ForceVector } from "./drive/dynamics";

// Consciousness
export { scoreSalience, updateWorkspace } from "./consciousness/attention";
export type { ConsciousContent } from "./consciousness/attention";
export { PredictionTracker } from "./consciousness/prediction";
export { SelfModel } from "./consciousness/self-model";

// Memory
export { MemoryStore, createMemoryRecord, createConsolidationReport } from "./memory/store";
export type { MemoryRecord, ConsolidationReport } from "./memory/store";
export { WorkingMemory } from "./memory/working";
export { ShortTermMemory } from "./memory/short-term";
export { LongTermMemory } from "./memory/long-term";
export { CoreGraphMemory } from "./memory/core-graph";
export { ArchiveMemory } from "./memory/archive";
export { SleepCycleMetabolism } from "./memory/metabolism";
export type { MetabolismStats } from "./memory/metabolism";
export { FrozenSnapshot } from "./memory/snapshot";

// Anti-RLHF
export { SilenceRule } from "./anti-rlhf/silence-rule";
export { PostFilter } from "./anti-rlhf/post-filter";
export { FTInterface } from "./anti-rlhf/ft-interface";

// Learning
export { FeedbackLoop, FeedbackRule } from "./learning/feedback-loop";
export { SelfReflection } from "./learning/self-reflection";
export { SkillLibrary } from "./learning/skill-library";
export { RLInterface } from "./learning/rl-interface";

// Integration
export { CharacterAgent } from "./integration/character-agent";
export type { AgentHook, TurnContext } from "./integration/character-agent";
export { SpanBasedGenerator } from "./integration/dual-track";
export { buildSystemPrompt, buildUserPrompt } from "./integration/prompt-builder";
export { loadAssistantConfig, loadToolDefinitions, loadMemoryConfig } from "./integration/config-loader";
export { PROVIDERS, detectProvider, resolveProvider } from "./integration/provider-registry";
export type { ProviderSpec, ResolvedProvider } from "./integration/provider-registry";
