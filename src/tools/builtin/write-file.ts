import { z } from "zod";
import { resolve, dirname } from "path";
import { mkdirSync, existsSync, writeFileSync } from "fs";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult, successResult } from "../types";

const params = z.object({
  path: z.string().describe("文件路径"),
  content: z.string().describe("要写入的内容"),
});

export const writeFileTool: ToolDef<z.infer<typeof params>, { path: string; chars: number }> = {
  name: "write_file",
  aliases: ["write"],
  description: "创建或覆盖文件。自动创建父目录。此操作不可撤销。",
  parameters: params,
  isReadOnly: false,
  isDestructive: true,
  isConcurrencySafe: false,
  riskLevel: "high",

  async execute(p, ctx: ToolContext): Promise<ToolResult<{ path: string; chars: number }>> {
    const filePath = resolve(ctx.workingDir, p.path);
    try {
      const dir = dirname(filePath);
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
      writeFileSync(filePath, p.content, "utf-8");
      return successResult(`Written: ${p.path} (${p.content.length} chars)`, { path: p.path, chars: p.content.length });
    } catch (e: any) {
      return errorResult(`Cannot write ${p.path}: ${e.message}`);
    }
  },

  formatResult(data: { path: string; chars: number }): string {
    return `Created ${data.path} (${data.chars} characters)`;
  },
  formatError(error: string, p: any): string {
    return `Error writing ${p.path}: ${error}`;
  },
};
