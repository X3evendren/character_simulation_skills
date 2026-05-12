/** Generation types — Span lifecycle, RepackContext, SpanOp, GenStatus */

export type SpanLayer = "fluid" | "stable" | "locked";

export interface Span {
  id: string;
  layer: SpanLayer;
  text: string;
  startPos: number;
  endPos: number;
  committedAt?: number;
}

export interface IntentState {
  topic: string;
  taskStage: "init" | "mid" | "final";
  constraints: string[];
}

export interface RepackContext {
  committedSpans: Span[];       // LOCKED + STABLE
  inflightSummary: string;      // 1-2 sentence semantic summary (not raw tokens)
  userInput: string;
  intentState: IntentState;
  memorySnapshot: string;
  psychologyState: any | null;  // last Cold Path result
  toolResults: ToolResult[];    // completed during abort — independent section
}

/** SpanRenderer operations */
export type SpanOp =
  | { type: "append"; span: Span }
  | { type: "patch"; spanId: string; newText: string }
  | { type: "lock"; spanId: string }
  | { type: "invalidate"; fromSpanId: string };

export type GenStatus = "idle" | "generating" | "aborting";

/** Minimal tool result interface — matches ToolResult from tools/base */
export interface ToolResult {
  name: string;
  success: boolean;
  output?: string;
  error?: string;
}
