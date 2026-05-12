/** Inflight Summarizer — compress interrupted fluid text to 1-2 sentence semantic summary.
 *  Primary: Psych model (fast, small). Fallback: rule-based last-sentence extraction.
 */
import type { Span } from "./types";

export interface SummarizerProvider {
  chat(
    messages: Array<{ role: string; content: string }>,
    temperature?: number,
    maxTokens?: number,
  ): Promise<{ content: string }>;
}

export class InflightSummarizer {
  private psychProvider: SummarizerProvider;

  constructor(psychProvider: SummarizerProvider) {
    this.psychProvider = psychProvider;
  }

  /** Compress inflight fluid spans into 1-2 sentence summary. */
  async summarize(fluidSpans: Span[]): Promise<string> {
    const text = fluidSpans.map(s => s.text).join("").trim();
    if (!text) return "";

    // Primary: Psych model
    try {
      const prompt = [
        "将以下未完成的对话内容压缩为1-2句中文摘要，只输出摘要，不要任何解释：",
        "",
        text.slice(-500),
      ].join("\n");

      const resp = await this.psychProvider.chat(
        [{ role: "user", content: prompt }],
        0.1,
        100,
      );

      const result = resp.content?.trim();
      if (result) return result;
    } catch {
      // fall through to rule-based
    }

    // Fallback: extract last complete sentence
    return this._extractLastSentence(text);
  }

  /** Rule-based: extract last sentence from text. */
  private _extractLastSentence(text: string): string {
    const sentences = text.split(/[。！？\n]/).filter(Boolean);
    const last = sentences.pop();
    if (!last) return "";
    const trimmed = last.trim();
    return trimmed.length > 50 ? `…${trimmed.slice(-50)}` : trimmed;
  }
}
