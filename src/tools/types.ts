import type { z } from "zod";

export type RiskLevel = "low" | "medium" | "high";

export interface ToolContext {
  workingDir: string;
  sessionId: string;
  onProgress?: (msg: string) => void;
  signal?: AbortSignal;
}

export interface ToolResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  output: string;
  truncated: boolean;
}

export interface ToolDef<I = any, O = any> {
  name: string;
  aliases?: string[];
  description: string;
  parameters: z.ZodType<I>;
  isReadOnly: boolean;
  isDestructive: boolean;
  isConcurrencySafe: boolean;
  riskLevel: RiskLevel;
  execute(params: I, ctx: ToolContext): Promise<ToolResult<O>>;
  formatResult(result: O, params: I): string;
  formatError(error: string, params: I): string;
}

export type PermissionBehavior = "allow" | "deny" | "ask";

export interface PermissionResult {
  behavior: PermissionBehavior;
  reason?: string;
  /** If behavior is "ask", this message is displayed to the user. */
  promptMessage?: string;
}

export function successResult<T = string>(output: string, data?: T, truncated?: boolean): ToolResult<T> {
  return { success: true, data: data as T, output, truncated: truncated ?? false };
}

export function errorResult<T = string>(error: string, output?: string): ToolResult<T> {
  return { success: false, error, output: output ?? error, truncated: false, data: undefined };
}
