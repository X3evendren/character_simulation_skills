/**
 * GuardPipeline — Multi-layer guardrail system.
 *
 * Gates are ordered and isolated. Each gate can inspect input, output,
 * tool calls, and tool results. Any gate can block or modify content.
 *
 * Architecture:
 *   Gate 0: Regex deny-list → zero latency
 *   Gate 1: Structured validation → Zod schema + value range
 *   Gate 2: Stateless semantic check → pattern-based content safety
 *   Gate 3: Stateful policy evaluation → cumulative behavior tracking
 *   Gate 4 (reserved): Deep semantic review → independent LLM-as-Judge
 */

export interface GateResult {
  passed: boolean;
  action: "allow" | "replace" | "block";
  replacement?: string;
  reason?: string;
}

export interface ToolCallInfo {
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultInfo {
  name: string;
  success: boolean;
  output?: string;
  error?: string;
}

export interface GuardGate {
  readonly name: string;
  /** Called on user input before processing. Return block/replace to intercept. */
  onInput?(input: string): GateResult | Promise<GateResult>;
  /** Called on model output before displaying. Return block/replace to modify. */
  onOutput?(output: string): GateResult | Promise<GateResult>;
  /** Called before tool execution. Return block to prevent. */
  onToolCall?(tool: ToolCallInfo): GateResult | Promise<GateResult>;
  /** Called after tool execution. May flag suspicious results. */
  onToolResult?(result: ToolResultInfo): GateResult | Promise<GateResult>;
}

export interface PipelineReport {
  gate: string;
  stage: string;
  action: string;
  reason?: string;
}

export class GuardPipeline {
  private gates: GuardGate[] = [];
  private reports: PipelineReport[] = [];
  /** Track consecutive tool failures per tool name */
  private toolFailureCount = new Map<string, number>();

  constructor(gates: GuardGate[] = []) {
    this.gates = gates;
  }

  addGate(gate: GuardGate): void {
    this.gates.push(gate);
  }

  /** Run input through all gates. Returns the (possibly modified) input, or null if blocked. */
  async checkInput(input: string): Promise<{ allowed: boolean; content: string; reports: PipelineReport[] }> {
    const stageReports: PipelineReport[] = [];
    let content = input;
    for (const gate of this.gates) {
      if (!gate.onInput) continue;
      try {
        const result = await gate.onInput(content);
        if (!result.passed || result.action === "block") {
          stageReports.push({ gate: gate.name, stage: "input", action: "block", reason: result.reason });
          this.reports.push(...stageReports);
          return { allowed: false, content: result.replacement ?? content, reports: stageReports };
        }
        if (result.action === "replace" && result.replacement !== undefined) {
          content = result.replacement;
          stageReports.push({ gate: gate.name, stage: "input", action: "replace", reason: result.reason });
        } else {
          stageReports.push({ gate: gate.name, stage: "input", action: "allow" });
        }
      } catch { /* gate failure must not crash the pipeline */ }
    }
    this.reports.push(...stageReports);
    return { allowed: true, content, reports: stageReports };
  }

  /** Run output through all gates. Returns the (possibly modified) output, or null if blocked. */
  async checkOutput(output: string): Promise<{ allowed: boolean; content: string; reports: PipelineReport[] }> {
    const stageReports: PipelineReport[] = [];
    let content = output;
    for (const gate of this.gates) {
      if (!gate.onOutput) continue;
      try {
        const result = await gate.onOutput(content);
        if (!result.passed || result.action === "block") {
          stageReports.push({ gate: gate.name, stage: "output", action: "block", reason: result.reason });
          this.reports.push(...stageReports);
          return { allowed: false, content: result.replacement ?? content, reports: stageReports };
        }
        if (result.action === "replace" && result.replacement !== undefined) {
          content = result.replacement;
          stageReports.push({ gate: gate.name, stage: "output", action: "replace", reason: result.reason });
        } else {
          stageReports.push({ gate: gate.name, stage: "output", action: "allow" });
        }
      } catch { /* gate failure must not crash the pipeline */ }
    }
    this.reports.push(...stageReports);
    return { allowed: true, content, reports: stageReports };
  }

  /** Check tool call before execution. */
  async checkToolCall(tool: ToolCallInfo): Promise<{ allowed: boolean; reason?: string }> {
    for (const gate of this.gates) {
      if (!gate.onToolCall) continue;
      try {
        const result = await gate.onToolCall(tool);
        if (!result.passed || result.action === "block") {
          this.reports.push({ gate: gate.name, stage: "tool_call", action: "block", reason: result.reason });
          return { allowed: false, reason: result.reason };
        }
      } catch { /* continue */ }
    }
    return { allowed: true };
  }

  /** Check tool result after execution. Updates failure tracking. */
  async checkToolResult(result: ToolResultInfo): Promise<{ flagged: boolean; reason?: string }> {
    // Update failure tracking
    if (!result.success) {
      const count = (this.toolFailureCount.get(result.name) ?? 0) + 1;
      this.toolFailureCount.set(result.name, count);
      if (count >= 3) {
        this.reports.push({ gate: "failure_tracker", stage: "tool_result", action: "block", reason: `${result.name} 连续失败 ${count} 次` });
        return { flagged: true, reason: `${result.name} 连续失败 ${count} 次` };
      }
    } else {
      this.toolFailureCount.set(result.name, 0);
    }

    for (const gate of this.gates) {
      if (!gate.onToolResult) continue;
      try {
        const check = await gate.onToolResult(result);
        if (!check.passed) {
          this.reports.push({ gate: gate.name, stage: "tool_result", action: "block", reason: check.reason });
          return { flagged: true, reason: check.reason };
        }
      } catch { /* continue */ }
    }
    return { flagged: false };
  }

  /** Reset per-session state (failure counters, etc.) */
  reset(): void {
    this.toolFailureCount.clear();
    this.reports = [];
  }

  /** Get recent reports for auditing */
  getReports(): PipelineReport[] { return [...this.reports]; }

  /** Get recent reports and clear */
  drainReports(): PipelineReport[] {
    const r = [...this.reports];
    this.reports = [];
    return r;
  }
}
