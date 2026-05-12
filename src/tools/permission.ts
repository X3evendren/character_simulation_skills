/** Permission System — 2-layer: rule-based + terminal confirmation. */

import { createInterface } from "readline";
import type { ToolDef, PermissionResult, ToolContext } from "./types";

const DANGEROUS_PATTERNS: Array<[RegExp, string]> = [
  [/rm\s+-rf\s+\//, "recursive root deletion"],
  [/sudo\s/, "privilege escalation"],
  [/git\s+push\s+--force/, "force push"],
  [/git\s+reset\s+--hard/, "hard reset"],
  [/mkfs\./, "filesystem format"],
  [/dd\s+if=/, "direct disk write"],
  [/>\s*\/dev\//, "device write"],
  [/chmod\s+777/, "world-writable permissions"],
  [/:\(\)\s*\{\s*:\|:&\s*\};:/, "fork bomb"],
];

export class PermissionRules {
  /** Check if a command contains dangerous patterns. */
  static auditCommand(command: string): { blocked: boolean; reason: string } {
    for (const [pattern, desc] of DANGEROUS_PATTERNS) {
      if (pattern.test(command)) {
        return { blocked: true, reason: `blocked: ${desc}` };
      }
    }
    return { blocked: false, reason: "" };
  }

  /** Determine permission behavior based on tool risk level. */
  static evaluate(tool: ToolDef, _params: any, _ctx: ToolContext): PermissionResult {
    // High risk → always ask
    if (tool.riskLevel === "high") {
      return { behavior: "ask", reason: `"${tool.name}" is a high-risk tool` };
    }

    // Medium risk → auto-allow in interactive mode
    if (tool.riskLevel === "medium") {
      return { behavior: "allow", reason: "medium risk, auto-allowed" };
    }

    // Low risk → auto-allow
    return { behavior: "allow", reason: "low risk" };
  }
}

/** Terminal confirmation — [y/N] prompt for dangerous operations. */
export class TerminalConfirm {
  private timeoutMs: number;

  constructor(timeoutMs = 30000) {
    this.timeoutMs = timeoutMs;
  }

  /** Ask user to confirm a tool execution. Returns true if approved. */
  async confirm(tool: ToolDef, params: any, ctx: ToolContext): Promise<boolean> {
    const summary = this._summarize(tool, params);
    const prompt = `\n⚠  ${summary}\n   Execute? [y/N] `;

    return new Promise((resolve) => {
      const rl = createInterface({ input: process.stdin, output: process.stdout });
      const timer = setTimeout(() => {
        rl.close();
        process.stdout.write("\n   (timed out, denied)\n");
        resolve(false);
      }, this.timeoutMs);

      rl.question(prompt, (answer: string) => {
        clearTimeout(timer);
        rl.close();
        resolve(answer.trim().toLowerCase() === "y");
      });
    });
  }

  private _summarize(tool: ToolDef, params: any): string {
    switch (tool.name) {
      case "exec_command":
        return `Run: ${params.command?.slice(0, 80) ?? "?"}`;
      case "write_file":
        return `Write: ${params.path ?? "?"} (${(params.content ?? "").length} chars)`;
      case "edit_file":
        return `Edit: ${params.path ?? "?"}`;
      case "web_fetch":
        return `Fetch: ${params.url?.slice(0, 60) ?? "?"}`;
      default:
        return `${tool.name}: ${JSON.stringify(params).slice(0, 80)}`;
    }
  }
}
