/** Span-Based Generator — Fast (FLUID→STABLE) + Slow (STABLE→LOCKED) + Tool calls.
 *  Replaces token-stream dual-track with span lifecycle management.
 */
import type { SpanOp } from "../../generation/types";
import type { ToolRegistry } from "../../tools/registry";
import type { ToolCall } from "./provider";

let _nextSpanId = 1;
function nextSpanId(): string { return `s${_nextSpanId++}`; }

interface StreamToken { text: string; done: boolean; toolCalls?: ToolCall[]; }

/** Convert callback-based chatStream to async iterator with abort support. */
async function* streamTokens(
  provider: any, messages: any[], temperature: number, maxTokens: number,
  tools: any, signal: AbortSignal,
): AsyncGenerator<StreamToken> {
  const buffer: string[] = [];
  let streamDone = false;
  let streamError: Error | null = null;
  let toolCalls: ToolCall[] = [];

  const promise = provider.chatStream(
    messages, temperature, maxTokens, tools,
    async (delta: string) => { buffer.push(delta); },
    "", signal,
  ).then((r: any) => { toolCalls = r.toolCalls ?? []; streamDone = true; })
   .catch((e: Error) => { streamError = e; streamDone = true; });

  let idx = 0;
  while (!streamDone) {
    if (signal.aborted) break;
    while (idx < buffer.length) { yield { text: buffer[idx], done: false }; idx++; }
    await new Promise(r => setTimeout(r, 30));
  }
  while (idx < buffer.length) { yield { text: buffer[idx], done: false }; idx++; }
  if (streamError) throw streamError;
  yield { text: "", done: true, toolCalls: toolCalls.length > 0 ? toolCalls : undefined };
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
  private toolRegistry?: ToolRegistry;
  private maxToolRounds = 10;

  constructor(fastProvider: any, slowProvider: any, toolRegistry?: ToolRegistry) {
    this.fastProvider = fastProvider;
    this.slowProvider = slowProvider;
    this.toolRegistry = toolRegistry;
  }

  async *generate(
    systemPrompt: string,
    userMessage: string,
    signal: AbortSignal,
    tools?: any,
  ): AsyncGenerator<SpanOp> {
    const messages: any[] = [
      { role: "system", content: systemPrompt },
      { role: "user", content: userMessage },
    ];

    // ═══════════════════════════════════════
    // Tool call loop
    // ═══════════════════════════════════════
    for (let round = 0; round < this.maxToolRounds && !signal.aborted; round++) {
      const lastToken: StreamToken = { text: "", done: false };

      for await (const token of streamTokens(
        this.fastProvider, messages, 0.6, 300, tools, signal,
      )) {
        if (signal.aborted) break;
        if (token.done) { Object.assign(lastToken, token); break; }
        // Stream text as FLUID spans
        if (token.text) {
          const spanId = nextSpanId();
          yield { type: "append", span: { id: spanId, layer: "fluid", text: token.text, startPos: 0, endPos: token.text.length } };
          yield { type: "lock", spanId };
        }
      }

      if (signal.aborted) return;

      // Check for tool calls
      const toolCalls = lastToken.toolCalls;
      if (!toolCalls || toolCalls.length === 0) break;

      // Execute tools
      if (this.toolRegistry) {
        const assistantMsg: any = { role: "assistant", content: "" };
        assistantMsg.tool_calls = toolCalls.map((tc: ToolCall) => ({
          id: tc.id, type: "function", function: { name: tc.name, arguments: JSON.stringify(tc.arguments) },
        }));
        messages.push(assistantMsg);

        for (const tc of toolCalls) {
          const result = await this.toolRegistry.execute(tc.name, tc.arguments, {
            workingDir: process.cwd(), sessionId: "",
          });
          messages.push({
            role: "tool", tool_call_id: tc.id,
            content: result.output,
          });
          // Yield tool result as a visible span
          const toolSpanId = nextSpanId();
          yield { type: "append", span: { id: toolSpanId, layer: "locked", text: `[${tc.name}] ${result.output.slice(0, 200)}`, startPos: 0, endPos: 0, committedAt: Date.now() } };
        }
      } else {
        break; // No registry, can't execute tools
      }
    }
  }
}
