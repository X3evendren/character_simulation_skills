import { z } from "zod";
import { resolve } from "path";
import { existsSync } from "fs";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult, successResult } from "../types";

const params = z.object({
  pattern: z.string().describe("glob 模式, 如 **/*.ts"),
  path: z.string().optional().describe("搜索根目录, 默认当前工作目录"),
});

export const searchFilesTool: ToolDef<z.infer<typeof params>, string> = {
  name: "search_files",
  aliases: ["glob"],
  description: "按 glob 模式查找文件。返回匹配文件路径列表，按修改时间排序。",
  parameters: params,
  isReadOnly: true,
  isDestructive: false,
  isConcurrencySafe: true,
  riskLevel: "low",

  async execute(p, ctx: ToolContext): Promise<ToolResult<string>> {
    const root = resolve(ctx.workingDir, p.path ?? ".");
    if (!existsSync(root)) return errorResult(`Directory not found: ${p.path ?? "."}`);

    try {
      const fg = await import("fast-glob");
      const globFn = (fg as any).default ?? fg.glob ?? fg;
      const matches = await globFn(p.pattern, {
        cwd: root,
        absolute: true,
        onlyFiles: true,
        followSymbolicLinks: false,
        ignore: ["**/node_modules/**", "**/.git/**"],
      });

      // Sort by mtime
      const { statSync } = await import("fs");
      const sorted = matches.sort((a, b) => {
        try { return statSync(b).mtimeMs - statSync(a).mtimeMs; } catch { return 0; }
      });

      const output = sorted.slice(0, 200).join("\n") || "(无匹配)";
      if (sorted.length > 200) {
        return successResult(output + `\n... 及其他 ${sorted.length - 200} 个文件`, output);
      }
      return successResult(output, output);
    } catch (e: any) {
      return errorResult(`search_files failed: ${e.message}`);
    }
  },

  formatResult(data: string): string { return data; },
  formatError(error: string, p: any): string {
    return `search_files failed for "${p.pattern}": ${error}`;
  },
};
