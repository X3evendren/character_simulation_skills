import { z } from "zod";
import { readFileSync, statSync, existsSync } from "fs";
import { resolve } from "path";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult, successResult } from "../types";
import { FileStateTracker } from "../file-state";

const params = z.object({
  path: z.string().describe("文件路径"),
  offset: z.number().optional().describe("起始行号(默认0)"),
  limit: z.number().optional().describe("最大行数(默认500)"),
});

const fileState = new FileStateTracker();

export const readFileTool: ToolDef<z.infer<typeof params>, string> = {
  name: "read_file",
  aliases: ["read"],
  description: "读取文件内容。返回带行号的文本。支持 offset/limit 控制范围。",
  parameters: params,
  isReadOnly: true,
  isDestructive: false,
  isConcurrencySafe: true,
  riskLevel: "low",

  async execute(p, ctx: ToolContext): Promise<ToolResult<string>> {
    const filePath = resolve(ctx.workingDir, p.path);
    if (!existsSync(filePath)) return errorResult(`File not found: ${p.path}`);

    try {
      const stat = statSync(filePath);
      if (stat.isDirectory()) return errorResult(`Path is a directory: ${p.path}`);

      const { unchanged, content } = fileState.recordRead(filePath);
      if (unchanged) {
        return successResult(`[File unchanged since last read: ${p.path}]`, "");
      }

      const lines = content!.split("\n");
      const offset = p.offset ?? 0;
      const limit = p.limit ?? 500;
      const chunk = lines.slice(offset, offset + limit);

      let output = chunk.map((line, i) => `${offset + i + 1}\t${line}`).join("\n");
      if (chunk.length < lines.length - offset) {
        output += `\n... (${lines.length - offset - chunk.length} more lines)`;
      }

      return successResult(output, content!);
    } catch (e: any) {
      return errorResult(`Cannot read ${p.path}: ${e.message}`);
    }
  },

  formatResult(data: string): string {
    return data;
  },

  formatError(error: string, p: any): string {
    return `Error reading ${p.path}: ${error}`;
  },
};
