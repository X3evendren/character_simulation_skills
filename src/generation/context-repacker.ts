/** Context Repacker — state snapshot + prompt rebuild.
 *  Key rule: never splice raw stream text. Only pack "state".
 */
import type { RepackContext, Span, IntentState, ToolResult } from "./types";

export interface RepackParams {
  committedSpans: Span[];
  inflightSummary: string;
  userInput: string;
  memorySnapshot: string;
  psychologyState: any | null;
  toolResults: ToolResult[];
  intentState: IntentState;
  characterConfig: { name: string; traits: string; essence?: string; rules?: string };
  capabilities: string;
  groundTruthText: string;
  affectiveResidueText: string;
  driveBiasText: string;
  selfNarrativeText: string;
  temporalHorizonText: string;
  isFirstTurn: boolean;
  taskMode: boolean;
}

export class ContextRepacker {
  repack(params: RepackParams): RepackContext {
    return {
      committedSpans: params.committedSpans,
      inflightSummary: params.inflightSummary,
      userInput: params.userInput,
      intentState: params.intentState,
      memorySnapshot: params.memorySnapshot,
      psychologyState: params.psychologyState,
      toolResults: params.toolResults,
    };
  }

  /** Build system prompt from repacked context — 7-layer structure. */
  buildPrompt(ctx: RepackContext, params: RepackParams): string {
    const parts: string[] = [];

    // Layer 0: Capability boundary
    parts.push(params.capabilities);

    // Layer 0.5: First turn awareness
    if (params.isFirstTurn) {
      parts.push("【重要 — 这是你第一次和这个用户对话】你没有和这个用户的任何历史记忆。不要假装知道ta昨天说了什么。不要编造类似上次我们聊到之类的话。你现在唯一知道的就是ta刚刚输入的内容。");
    }

    // Layer 1: Ground Truth
    if (params.groundTruthText) parts.push(params.groundTruthText);

    // Layer 1.5: Passive affective sediment
    if (params.affectiveResidueText) {
      parts.push(params.affectiveResidueText);
    }

    // Layer 1.6: Drive sublimation
    if (params.driveBiasText) {
      parts.push(params.driveBiasText);
    }

    // Layer 1.7: Self narrative
    if (params.selfNarrativeText) {
      parts.push(params.selfNarrativeText);
    }

    // Layer 1.8: Temporal horizon
    if (params.temporalHorizonText) {
      parts.push(params.temporalHorizonText);
    }

    // Layer 2: Task mode gate
    if (params.taskMode) {
      parts.push("【任务模式】简洁准确，禁止抒情、隐喻、发散。只陈述事实。");
    } else {
      parts.push("【闲聊模式】可以自然表达情感和个性。回应简短(2-3句)。");
    }

    // Layer 3: Character identity
    parts.push(`【角色锚定】你是 ${params.characterConfig.name}，不是"一个AI助手"。`);
    parts.push(`人格: ${params.characterConfig.traits}`);
    if (params.characterConfig.rules) {
      parts.push(`【行为准则】\n${params.characterConfig.rules}`);
    }

    // Layer 4: Committed context (LOCKED + STABLE)
    if (ctx.committedSpans.length > 0) {
      const lockedText = ctx.committedSpans
        .filter(s => s.layer === "locked")
        .map(s => s.text).join("");
      const stableText = ctx.committedSpans
        .filter(s => s.layer === "stable")
        .map(s => s.text).join("");

      if (lockedText) {
        parts.push(`【已确认上下文 — 不可修改】\n${lockedText}`);
      }
      if (stableText) {
        parts.push(`【待确认上下文 — 可微调但不要重写】\n${stableText}`);
      }
    }

    // Layer 5: Inflight summary (if any — from interrupted generation)
    if (ctx.inflightSummary) {
      parts.push(`【上一轮中断时的内容摘要】\n${ctx.inflightSummary}\n请自然延续，不要重复已输出的内容。`);
    }

    // Layer 6: Background tool results (independent, not in memory)
    if (ctx.toolResults.length > 0) {
      const toolLines = ctx.toolResults.map(tr => {
        const status = tr.success ? "OK" : "FAIL";
        const out = (tr.output || tr.error || "").slice(0, 200);
        return `- [${status}] ${tr.name}: ${out}`;
      });
      parts.push(`【后台工具结果】\n${toolLines.join("\n")}`);
    }

    // Layer 7: User input
    parts.push(`【用户输入】\n${ctx.userInput}`);

    // Layer 8: Memory snapshot
    if (ctx.memorySnapshot) parts.push(ctx.memorySnapshot);

    // Layer 9: Psychology state (from last Cold Path — emotional tone only)
    if (ctx.psychologyState) {
      const emo = ctx.psychologyState.emotion;
      if (emo && emo.dominant !== "neutral") {
        parts.push(`【当前感受】${emo.dominant} (${((emo.intensity ?? 0.5) * 100).toFixed(0)}%) — 影响语气，不影响事实判断`);
      }
    }

    // Layer 10: Intent
    parts.push(`【意图】话题: ${ctx.intentState.topic}, 阶段: ${ctx.intentState.taskStage}`);
    if (ctx.intentState.constraints.length > 0) {
      parts.push(`约束: ${ctx.intentState.constraints.join(", ")}`);
    }

    // Layer 11: Task instruction
    parts.push("【任务】自然延续对话。不要重复已确认的内容。如果话题切换，平滑过渡。如果是同一话题，继续深入。");

    // Layer 12: Anti-RLHF anchor
    parts.push("【反RLHF锚定】回应简短。不解释动机。不分析自己。");

    return parts.join("\n\n");
  }
}

// ═══════════════════════════════════════
// Intent Detection — hybrid: rules + lightweight model
// ═══════════════════════════════════════

const TOPIC_KEYWORDS: Record<string, string[]> = {
  "technical": ["代码", "编程", "架构", "API", "服务器", "数据库", "算法", "性能", "bug", "部署"],
  "emotional": ["感觉", "心情", "难过", "开心", "焦虑", "压力", "孤独", "累"],
  "philosophical": ["意义", "人生", "为什么", "存在", "自由", "意识"],
  "task": ["帮我", "写", "查", "找", "修改", "创建", "删除", "运行", "执行", "安装"],
  "casual": ["你好", "嗨", "哈哈", "嗯", "哦", "晚安", "早安"],
  "help": ["求助", "帮忙", "建议", "怎么", "如何", "推荐"],
};

const TASK_KEYWORDS = [
  "读", "打开", "查看", "显示", "列出", "搜索", "找", "查找",
  "执行", "运行", "总结", "概括", "分析", "修改", "编辑", "写", "创建",
  "read", "open", "cat", "ls", "find", "grep", "run", "exec",
];

export function detectIntent(input: string): IntentState {
  const lower = input.toLowerCase();

  // Determine topic
  let topic = "general";
  for (const [cat, kws] of Object.entries(TOPIC_KEYWORDS)) {
    if (kws.some(kw => lower.includes(kw))) { topic = cat; break; }
  }

  // Determine taskStage
  const taskMode = TASK_KEYWORDS.some(kw => lower.includes(kw));
  let taskStage: "init" | "mid" | "final" = "init";
  if (input.length < 10) taskStage = "final";           // short input likely follow-up
  else if (taskMode) taskStage = "init";                  // task keyword = new task
  else if (lower.includes("继续") || lower.includes("然后")) taskStage = "mid";

  // Constraints
  const constraints: string[] = [];
  if (taskMode) constraints.push("task_mode");
  if (topic === "emotional") constraints.push("emotionally_aware");
  if (topic === "help") constraints.push("be_helpful_precise");

  return { topic, taskStage, constraints };
}

/** Lightweight intent detection via Psych model — for cases rules can't decide. */
export async function detectIntentWithModel(
  input: string,
  provider: { chat(messages: Array<{ role: string; content: string }>, t?: number, max?: number): Promise<{ content: string }> },
): Promise<IntentState> {
  try {
    const prompt = `分析用户输入，输出JSON: {"topic":"technical|emotional|philosophical|task|casual|help|general","taskStage":"init|mid|final","constraints":[]}\n\n输入: ${input}`;
    const resp = await provider.chat([{ role: "user", content: prompt }], 0.1, 100);
    const parsed = JSON.parse(resp.content || "{}");
    return {
      topic: parsed.topic || "general",
      taskStage: parsed.taskStage || "init",
      constraints: parsed.constraints || [],
    };
  } catch {
    return detectIntent(input); // fallback to rule-based
  }
}
