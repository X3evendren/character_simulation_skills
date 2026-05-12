/** Span-Based Generator — Fast (FLUID→STABLE) + Slow (STABLE→LOCKED).
 *  Replaces token-stream dual-track with span lifecycle management.
 */
import type { SpanOp } from "../../generation/types";

let _nextSpanId = 1;
function nextSpanId(): string { return `s${_nextSpanId++}`; }

// ═══════════════════════════════════════
// Span token helper
// ═══════════════════════════════════════

interface StreamToken {
  text: string;
  done: boolean;
}

/** Convert callback-based chatStream to async iterator with abort support. */
async function* streamTokens(
  provider: any,
  messages: Array<{ role: string; content: string }>,
  temperature: number,
  maxTokens: number,
  signal: AbortSignal,
): AsyncGenerator<StreamToken> {
  const buffer: string[] = [];
  let done = false;

  const promise = provider.chatStream(
    messages, temperature, maxTokens, undefined,
    async (delta: string) => { buffer.push(delta); },
    "", signal,
  );

  // Poll buffer until stream completes or aborted
  let idx = 0;
  while (!done) {
    if (signal.aborted) { done = true; break; }

    while (idx < buffer.length) {
      yield { text: buffer[idx], done: false };
      idx++;
    }

    // Check if stream finished
    try {
      const result = await Promise.race([
        promise.then(() => "done"),
        new Promise(r => setTimeout(r, 50)).then(() => "timeout"),
      ]);
      if (result === "done") {
        // Flush remaining
        while (idx < buffer.length) {
          yield { text: buffer[idx], done: false };
          idx++;
        }
        done = true;
      }
    } catch {
      done = true;
    }
  }

  yield { text: "", done: true };
}

// ═══════════════════════════════════════
// Sentence boundary detection
// ═══════════════════════════════════════

const SENTENCE_END = /[。！？\n]/;
const MIN_SENTENCE_LEN = 4;

function isSentenceBoundary(text: string): boolean {
  if (text.length < MIN_SENTENCE_LEN) return false;
  return SENTENCE_END.test(text[text.length - 1]);
}

// ═══════════════════════════════════════
// SpanBasedGenerator
// ═══════════════════════════════════════

export class SpanBasedGenerator {
  private fastProvider: any;
  private slowProvider: any;

  constructor(fastProvider: any, slowProvider: any) {
    this.fastProvider = fastProvider;
    this.slowProvider = slowProvider;
  }

  async *generate(
    systemPrompt: string,
    userMessage: string,
    signal: AbortSignal,
  ): AsyncGenerator<SpanOp> {
    const messages = [
      { role: "system", content: systemPrompt },
      { role: "user", content: userMessage },
    ];

    let startPos = 0;
    const stableSpanIds: string[] = [];

    // ═══════════════════════════════════════
    // Phase 1: Fast Track — FLUID → STABLE at sentence boundaries
    // ═══════════════════════════════════════
    let buffer = "";

    for await (const token of streamTokens(
      this.fastProvider, messages, 0.6, 300, signal,
    )) {
      if (signal.aborted || token.done) break;

      buffer += token.text;

      if (isSentenceBoundary(buffer)) {
        const spanId = nextSpanId();
        const endPos = startPos + buffer.length;

        // Emit FLUID span
        yield { type: "append", span: { id: spanId, layer: "fluid", text: buffer, startPos, endPos } };

        // FLUID → STABLE (auto-commit at sentence boundary)
        yield { type: "lock", spanId };
        stableSpanIds.push(spanId);

        startPos = endPos;
        buffer = "";
      }
    }

    // Flush remaining buffer as FLUID (incomplete sentence)
    if (buffer.trim() && !signal.aborted) {
      const spanId = nextSpanId();
      const endPos = startPos + buffer.length;
      yield { type: "append", span: { id: spanId, layer: "fluid", text: buffer, startPos, endPos } };
      yield { type: "lock", spanId };
      stableSpanIds.push(spanId);
    }

    if (signal.aborted) {
      // Invalidate any remaining FLUID
      if (stableSpanIds.length > 0) {
        yield { type: "invalidate", fromSpanId: stableSpanIds[stableSpanIds.length - 1] };
      }
      return;
    }

    // ═══════════════════════════════════════
    // Phase 2: Slow Track — STABLE → LOCKED (background)
    // ═══════════════════════════════════════
    if (stableSpanIds.length === 0) return;

    const slowMessages = [
      { role: "system", content: `${systemPrompt}\n\n【核实任务】检查已输出的内容是否与事实一致。如有错误请修正。如果正确，回复"OK"。` },
      { role: "user", content: `已输出内容:\n${buffer}\n\n用户输入: ${userMessage}\n\n请核实并修正（如有必要）。` },
    ];

    try {
      const slowResp = await this.slowProvider.chat(
        slowMessages, 0.3, 1000, undefined, "", signal,
      );

      const slowContent: string = slowResp?.content ?? "";

      if (slowContent && slowContent.trim().toUpperCase() !== "OK" && slowContent.trim()) {
        // Slow has corrections — patch last STABLE span
        const lastStableId = stableSpanIds[stableSpanIds.length - 1];
        if (lastStableId) {
          yield { type: "patch", spanId: lastStableId, newText: slowContent.trim() };
        }
      }

      // STABLE → LOCKED for all verified spans
      for (const spanId of stableSpanIds) {
        yield { type: "lock", spanId };
      }
    } catch {
      // Slow failed — STABLE stays as-is (degraded but not broken)
    }
  }
}
