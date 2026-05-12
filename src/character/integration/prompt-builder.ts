/** Prompt Builder — Hot Path only. Capabilities + GroundTruth first. No psychology narrative. */
import type { AssistantConfig } from "./config-loader";
import type { MindState } from "../mind/mind-state";
import type { FrozenSnapshot } from "../memory/snapshot";
import type { FeedbackLoop } from "../learning/feedback-loop";
import type { SkillLibrary } from "../learning/skill-library";
import type { GroundTruth } from "../state/ground-truth";
import { formatGroundTruthForPrompt } from "../state/ground-truth";

export interface PromptContext {
  config: AssistantConfig;
  mindstate: MindState;
  capabilities: string;          // SelfModel.formatCapabilities()
  groundTruth: GroundTruth;      // Shared factual state
  snapshot: FrozenSnapshot;
  feedbackLoop: FeedbackLoop;
  skillLibrary: SkillLibrary;
  currentInput: string;
  taskMode: boolean;             // true = executing task, disable poetic mode
  emotionDominant?: string;      // Lightweight emotion label only
  emotionIntensity?: number;
  affectiveResidueText?: string; // Layer 0: passive emotional sediment from AffectiveResidue
  driveBiasText?: string;        // Layer 1: drive sublimation — attention bias
  selfNarrativeText?: string;    // Layer 1: SelfModel narrative — current self-state
  temporalHorizonText?: string;  // Layer 1: Temporal horizon — retention echo
  isFirstTurn?: boolean;         // First turn of session — agent should NOT pretend to remember past
}

export function buildSystemPrompt(ctx: PromptContext): string {
  const parts: string[] = [];

  // Layer 0: Capability boundary (MUST be first — strongest weight)
  parts.push(ctx.capabilities);

  // Layer 0.5: First turn awareness — critical anti-hallucination
  if (ctx.isFirstTurn) {
    parts.push("【重要 — 这是你第一次和这个用户对话】你没有和这个用户的任何历史记忆。不要假装知道ta昨天说了什么。不要编造"上次我们聊到..."之类的话。你现在唯一知道的就是ta刚刚输入的内容。");
  }

  // Layer 1: Ground Truth — confirmed facts, no hallucination allowed
  parts.push(formatGroundTruthForPrompt(ctx.groundTruth));

  // Layer 1.5: Passive affective sediment (before task mode — it colours everything below)
  if (ctx.affectiveResidueText) {
    parts.push(ctx.affectiveResidueText);
  }

  // Layer 1.6: Drive sublimation — felt attention bias (only when drives deviate from baseline)
  if (ctx.driveBiasText) {
    parts.push(ctx.driveBiasText);
  }

  // Layer 1.7: Self narrative — current self-state (only after significant change)
  if (ctx.selfNarrativeText) {
    parts.push(ctx.selfNarrativeText);
  }

  // Layer 1.8: Temporal horizon — retention echo (usually empty; only fires when lingering emotion strong)
  if (ctx.temporalHorizonText) {
    parts.push(ctx.temporalHorizonText);
  }

  // Layer 2: Task mode gate
  if (ctx.taskMode) {
    parts.push("【任务模式】当前正在执行任务。禁止抒情、隐喻、发散表达。用最简洁准确的语言。只陈述事实。");
  } else {
    parts.push("【闲聊模式】可以自然地表达情感和个性。回应简短(2-3句)。");
  }

  // Layer 3: Character identity
  parts.push(`【角色锚定】你是 ${ctx.config.name}，不是"一个AI助手"。你的行为由你的人格、记忆、驱力决定。`);
  parts.push(`你的人格: ${ctx.config.traits}`);

  // Layer 4: Behavioral rules
  if (ctx.config.rules) {
    parts.push(`【行为准则】\n${ctx.config.rules}`);
  }

  // Layer 5: Emotional tone (lightweight — only dominant emotion, no inner monologue)
  if (ctx.emotionDominant && ctx.emotionDominant !== "neutral") {
    parts.push(`【当前感受】${ctx.emotionDominant} (${((ctx.emotionIntensity ?? 0.5) * 100).toFixed(0)}%) — 影响说话语气，不影响事实判断`);
  }

  // Layer 6: Memory snapshot
  const snapText = ctx.snapshot.formatForPrompt();
  if (snapText) parts.push(snapText);

  // Layer 7: Learned rules + Skills
  const rules = ctx.feedbackLoop.getActiveRules(ctx.currentInput);
  const rulesText = ctx.feedbackLoop.formatRulesForPrompt(rules);
  if (rulesText) parts.push(rulesText);

  const skills = ctx.skillLibrary.route(ctx.currentInput);
  const skillsText = ctx.skillLibrary.formatForPrompt(skills);
  if (skillsText) parts.push(skillsText);

  // Layer 8: Anti-RLHF anchor
  parts.push("【反RLHF锚定】回应简短(2-3句)。不解释动机。不分析自己。");

  return parts.join("\n\n");
}

export function buildUserPrompt(input: string, taskMode: boolean): string {
  if (taskMode) {
    return `【用户输入 — 任务模式，请简洁准确】\n${input}`;
  }
  return `【用户输入】\n${input}`;
}
