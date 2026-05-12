import { z } from "zod";
import type { ToolDef, ToolResult, ToolContext } from "../types";
import { errorResult, successResult } from "../types";

const params = z.object({
  url: z.string().describe("网页 URL"),
  prompt: z.string().optional().describe("提取信息的提示"),
});

// SSRF protection: block private/internal IPs
const BLOCKED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]", "169.254", "10.", "172.16.", "192.168."];

function isBlockedHost(hostname: string): boolean {
  return BLOCKED_HOSTS.some(h => hostname.includes(h) || hostname === h);
}

export const webFetchTool: ToolDef<z.infer<typeof params>, string> = {
  name: "web_fetch",
  aliases: ["fetch"],
  description: "获取网页内容并提取文本。用于查阅在线文档或网页。",
  parameters: params,
  isReadOnly: true,
  isDestructive: false,
  isConcurrencySafe: true,
  riskLevel: "medium",

  async execute(p, ctx: ToolContext): Promise<ToolResult<string>> {
    // SSRF check
    try {
      const url = new URL(p.url);
      if (isBlockedHost(url.hostname)) {
        return errorResult(`SSRF blocked: ${url.hostname} is a private/internal address`);
      }
    } catch {
      return errorResult(`Invalid URL: ${p.url}`);
    }

    try {
      const resp = await fetch(p.url, {
        headers: { "User-Agent": "CharacterMind/3.0" },
        signal: ctx.signal ?? undefined,
        redirect: "follow",
      });

      if (!resp.ok) return errorResult(`HTTP ${resp.status}: ${resp.statusText}`);

      const html = await resp.text();
      // Strip scripts and styles, extract text
      let text = html.replace(/<script[^>]*>.*?<\/script>/gis, "")
        .replace(/<style[^>]*>.*?<\/style>/gis, "")
        .replace(/<[^>]+>/g, " ")
        .replace(/&[a-z]+;/g, " ")
        .replace(/\s+/g, " ")
        .trim();

      const maxChars = 8000;
      const truncated = text.length > maxChars;
      text = text.slice(0, maxChars);

      return successResult(text, text, truncated);
    } catch (e: any) {
      return errorResult(`web_fetch failed: ${e.message}`);
    }
  },

  formatResult(data: string): string { return data; },
  formatError(error: string): string { return `Fetch error: ${error}`; },
};
