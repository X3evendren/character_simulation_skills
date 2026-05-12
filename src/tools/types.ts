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

export function successResult<T>(output: string, data?: T, truncated = false): ToolResult<T> {
  return { success: true, data, output, truncated };
}

export function errorResult(error: string, output?: string): ToolResult {
  return { success: false, error, output: output ?? error, truncated: false };
}
