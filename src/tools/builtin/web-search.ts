import { z } from "zod";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult } from "../types";

const params = z.object({
  query: z.string().describe("搜索查询"),
});

export const webSearchTool: ToolDef<z.infer<typeof params>, string> = {
  name: "web_search",
  aliases: ["search"],
  description: "搜索网页。需要配置搜索 API key。当前为 stub。",
  parameters: params,
  isReadOnly: true,
  isDestructive: false,
  isConcurrencySafe: true,
  riskLevel: "low",

  async execute(p, ctx: ToolContext): Promise<ToolResult<string>> {
    return errorResult("web_search requires a search API key. Set WEB_SEARCH_API_KEY to enable.");
  },

  formatResult(): string { return ""; },
  formatError(error: string): string { return error; },
};
