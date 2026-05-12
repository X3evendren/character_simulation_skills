import { z } from "zod";
import { resolve } from "path";
import { execSync } from "child_process";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult, successResult } from "../types";

const params = z.object({
  pattern: z.string().describe("正则表达式"),
  path: z.string().optional().describe("搜索目录或文件，默认当前工作目录"),
  glob: z.string().optional().describe("文件名过滤, 如 *.ts"),
});

export const searchContentTool: ToolDef<z.infer<typeof params>, string> = {
  name: "search_content",
  aliases: ["grep"],
  description: "在文件内容中搜索正则表达式。使用 ripgrep (rg)。",
  parameters: params,
  isReadOnly: true,
  isDestructive: false,
  isConcurrencySafe: true,
  riskLevel: "low",

  async execute(p, ctx: ToolContext): Promise<ToolResult<string>> {
    const searchPath = resolve(ctx.workingDir, p.path ?? ".");
    try {
      const args = ["--line-number", "--no-heading", "--color=never", "--no-ignore-vcs", p.pattern];
      if (p.glob) args.push("--glob", p.glob);
      args.push(searchPath);

      const stdout = execSync(`rg ${args.map(a => `"${a}"`).join(" ")}`, {
        cwd: ctx.workingDir, encoding: "utf-8", timeout: 30000, maxBuffer: 5 * 1024 * 1024,
      });
      const lines = stdout.trim().split("\n").filter(Boolean);
      const output = lines.slice(0, 100).join("\n") || "(无匹配)";
      const truncated = lines.length > 100;
      if (truncated) return successResult(output + `\n... 及其他 ${lines.length - 100} 条`, output, true);
      return successResult(output, output);
    } catch (e: any) {
      if (e.status === 1) return successResult("(无匹配)", "");
      if (e.message?.includes("not found") || e.message?.includes("rg")) {
        return errorResult("rg (ripgrep) is not installed. Install it: https://github.com/BurntSushi/ripgrep");
      }
      return errorResult(`search_content failed: ${e.message}`);
    }
  },

  formatResult(data: string): string { return data; },
  formatError(error: string, p: any): string {
    return `search_content failed for "${p.pattern}": ${error}`;
  },
};
