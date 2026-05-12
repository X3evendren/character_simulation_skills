import { z } from "zod";
import { execSync } from "child_process";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult, successResult } from "../types";

const params = z.object({
  command: z.string().describe("要执行的 Shell 命令"),
  timeout: z.number().optional().describe("超时毫秒数(默认120000)"),
});

export const execCommandTool: ToolDef<z.infer<typeof params>, string> = {
  name: "exec_command",
  aliases: ["exec", "bash"],
  description: "执行 Shell 命令并返回输出。危险命令会被拒绝。",
  parameters: params,
  isReadOnly: false,
  isDestructive: true,
  isConcurrencySafe: false,
  riskLevel: "high",

  async execute(p, ctx: ToolContext): Promise<ToolResult<string>> {
    try {
      const timeout = p.timeout ?? 120000;
      const stdout = execSync(p.command, {
        cwd: ctx.workingDir,
        encoding: "utf-8",
        timeout,
        maxBuffer: 2 * 1024 * 1024,
        shell: process.platform === "win32" ? "cmd.exe" : "/bin/bash",
      });
      return successResult(stdout.trim() || "(无输出)", stdout);
    } catch (e: any) {
      const stderr = e.stderr ?? "";
      const stdout = e.stdout ?? "";
      const output = [stdout, stderr].filter(Boolean).join("\n").trim() || "(无输出)";
      if (e.killed) return errorResult(`Command timed out`, output);
      return errorResult(`${e.message}`, output || e.message);
    }
  },

  formatResult(data: string): string { return data; },
  formatError(error: string): string {
    return `Command error: ${error}`;
  },
};
