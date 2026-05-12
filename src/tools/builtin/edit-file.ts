import { z } from "zod";
import { resolve } from "path";
import { existsSync, readFileSync, writeFileSync } from "fs";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult, successResult } from "../types";
import { FileStateTracker } from "../file-state";

const params = z.object({
  path: z.string().describe("文件路径"),
  old_string: z.string().describe("要替换的文本（必须精确匹配，且唯一）"),
  new_string: z.string().describe("替换后的文本"),
});

const fileState = new FileStateTracker();

export const editFileTool: ToolDef<z.infer<typeof params>, string> = {
  name: "edit_file",
  aliases: ["edit"],
  description: "精确替换文件中的字符串。old_string 必须在文件中恰好出现一次，否则拒绝执行。",
  parameters: params,
  isReadOnly: false,
  isDestructive: true,
  isConcurrencySafe: false,
  riskLevel: "high",

  async execute(p, ctx: ToolContext): Promise<ToolResult<string>> {
    const filePath = resolve(ctx.workingDir, p.path);
    if (!existsSync(filePath)) return errorResult(`File not found: ${p.path}`);

    // Check read-before-write
    const warning = fileState.checkReadBeforeWrite(filePath);
    if (warning) {
      // Don't block, but prepend warning to output
    }

    try {
      const text = readFileSync(filePath, "utf-8");
      const count = text.split(p.old_string).length - 1;

      if (count === 0) return errorResult(`"${p.old_string.slice(0, 80)}" not found in ${p.path}`);
      if (count > 1) return errorResult(`"${p.old_string.slice(0, 80)}" appears ${count} times in ${p.path}. Old string must be unique. Provide more surrounding context.`);

      const newText = text.replace(p.old_string, p.new_string);
      writeFileSync(filePath, newText, "utf-8");
      return successResult(`Replaced 1 occurrence in ${p.path}`, `Replaced in ${p.path}`);
    } catch (e: any) {
      return errorResult(`Cannot edit ${p.path}: ${e.message}`);
    }
  },

  formatResult(data: string): string { return data; },
  formatError(error: string, p: any): string {
    return `Error editing ${p.path}: ${error}`;
  },
};
