/**
 * Ground Truth — Shared factual state that separates "what's true" from "what's felt".
 * Psychology engine CANNOT write here. Only tool results and user-confirmed facts.
 */

export interface FileState {
  path: string;
  loaded: boolean;
  content?: string;
  error?: string;
}

export interface TaskState {
  type: "idle" | "reading" | "editing" | "executing" | "searching";
  description: string;
  startTime: number;
}

export interface ToolResultEntry {
  tool: string;
  success: boolean;
  summary: string;
  timestamp: number;
}

export interface GroundTruth {
  files: Map<string, FileState>;
  currentTask: TaskState;
  lastToolResults: ToolResultEntry[];
  facts: string[];
}

export function createGroundTruth(): GroundTruth {
  return {
    files: new Map(),
    currentTask: { type: "idle", description: "", startTime: 0 },
    lastToolResults: [],
    facts: [],
  };
}

/** Mark a file as loaded (successful read) */
export function gtFileLoaded(gt: GroundTruth, path: string, content: string): void {
  gt.files.set(path, { path, loaded: true, content });
  gt.facts.push(`文件 ${path} 已成功读取 (${content.length} 字符)`);
  if (gt.facts.length > 50) gt.facts = gt.facts.slice(-50);
}

/** Mark a file as failed (read error) */
export function gtFileFailed(gt: GroundTruth, path: string, error: string): void {
  gt.files.set(path, { path, loaded: false, error });
  gt.facts.push(`文件 ${path} 读取失败: ${error}`);
  if (gt.facts.length > 50) gt.facts = gt.facts.slice(-50);
}

/** Record a tool result */
export function gtRecordTool(gt: GroundTruth, tool: string, success: boolean, summary: string): void {
  gt.lastToolResults.push({ tool, success, summary, timestamp: Date.now() / 1000 });
  if (gt.lastToolResults.length > 20) gt.lastToolResults = gt.lastToolResults.slice(-20);
}

/** Set current task type */
export function gtSetTask(gt: GroundTruth, type: TaskState["type"], description: string): void {
  gt.currentTask = { type, description, startTime: Date.now() / 1000 };
}

/** Add a user-confirmed fact */
export function gtAddFact(gt: GroundTruth, fact: string): void {
  gt.facts.push(fact);
  if (gt.facts.length > 50) gt.facts = gt.facts.slice(-50);
}

/** Format for prompt injection */
export function formatGroundTruthForPrompt(gt: GroundTruth): string {
  const lines: string[] = ["【已确认的事实 — 不可虚构，不可推翻】"];

  if (gt.currentTask.type !== "idle") {
    lines.push(`当前任务: ${gt.currentTask.type} — ${gt.currentTask.description}`);
  }

  for (const [path, fs] of gt.files) {
    if (fs.loaded) lines.push(`文件 ${path}: 已加载 (${(fs.content ?? "").length} 字符)`);
    else lines.push(`文件 ${path}: ${fs.error ?? "未加载"}`);
  }

  for (const tr of gt.lastToolResults.slice(-5)) {
    lines.push(`工具 ${tr.tool}: ${tr.success ? "成功" : "失败"} — ${tr.summary}`);
  }

  for (const f of gt.facts.slice(-10)) lines.push(`事实: ${f}`);

  if (lines.length === 1) lines.push("(尚无已确认的事实)");
  return lines.join("\n");
}
