/** Span-Based Generator — Fast (FLUID→STABLE) + Slow (STABLE→LOCKED) + Tool calls. */
import type { SpanOp } from "../generation/types";
import type { ToolRegistry } from "../tools/registry";
import type { ToolCall } from "./provider";
import type { Tracer } from "../telemetry";

let _nextSpanId = 1;
function nextSpanId(): string { return `s${_nextSpanId++}`; }

interface StreamToken { text: string; done: boolean; toolCalls?: ToolCall[]; reasoningContent?: string; }
const SENTENCE_END = /[。！？\n]/;
const MIN_SENTENCE_LEN = 4;

function isSentenceBoundary(text: string): boolean {
  if (text.length < MIN_SENTENCE_LEN) return false;
  return SENTENCE_END.test(text[text.length - 1]);
}

/** Convert callback-based chatStream to async iterator with abort support. */
async function* streamTokens(
  provider: any, messages: any[], temperature: number, maxTokens: number,
  tools: any, signal: AbortSignal,
): AsyncGenerator<StreamToken> {
  const buffer: string[] = [];
  let streamDone = false;
  let streamError: Error | null = null;
  let toolCalls: ToolCall[] = [];
  let reasoningContent = "";

  const promise = provider.chatStream(
    messages, temperature, maxTokens, tools,
    async (delta: string) => { buffer.push(delta); },
    "", signal,
  ).then((r: any) => { toolCalls = r.toolCalls ?? []; reasoningContent = r.reasoningContent ?? ""; streamDone = true; })
   .catch((e: Error) => { streamError = e; streamDone = true; });

  let idx = 0;
  while (!streamDone) {
    if (signal.aborted) break;
    while (idx < buffer.length) { yield { text: buffer[idx], done: false }; idx++; }
    await new Promise(r => setTimeout(r, 30));
  }
  while (idx < buffer.length) { yield { text: buffer[idx], done: false }; idx++; }
  if (streamError) throw streamError;
  yield { text: "", done: true, toolCalls: toolCalls.length > 0 ? toolCalls : undefined, reasoningContent: reasoningContent || undefined };
}

export class SpanBasedGenerator {
  private fastProvider: any;
  private slowProvider: any;
  private toolRegistry?: ToolRegistry;
  private tracer?: Tracer;
  private maxToolRounds = 10;

  constructor(fastProvider: any, slowProvider: any, toolRegistry?: ToolRegistry, tracer?: Tracer) {
    this.fastProvider = fastProvider;
    this.slowProvider = slowProvider;
    this.toolRegistry = toolRegistry;
    this.tracer = tracer;
  }

  async *generate(
    systemPrompt: string, userMessage: string, signal: AbortSignal,
    tools?: any, temperature = 0.6, maxTokens = 300,
  ): AsyncGenerator<SpanOp> {
    const effectiveTools = tools ?? this.toolRegistry?.getDefinitions();
    const messages: any[] = [
      { role: "system", content: systemPrompt },
      { role: "user", content: userMessage },
    ];

    for (let round = 0; round < this.maxToolRounds && !signal.aborted; round++) {
      const lastToken: StreamToken = { text: "", done: false };
      let buffer = "";
      let startPos = 0;

      const chatTTFT = performance.now();
      let firstToken = true;
      let ttftMs = 0;

      for await (const token of streamTokens(
        this.fastProvider, messages, temperature, maxTokens, effectiveTools, signal,
      )) {
        if (signal.aborted) break;
        if (firstToken && token.text) {
          ttftMs = performance.now() - chatTTFT;
          firstToken = false;
        }
        if (token.done) { Object.assign(lastToken, token); break; }
        if (token.text) {
          buffer += token.text;
          if (isSentenceBoundary(buffer)) {
            const spanId = nextSpanId();
            const endPos = startPos + buffer.length;
            yield { type: "append", span: { id: spanId, layer: "fluid", text: buffer, startPos, endPos } };
            yield { type: "lock", spanId };
            startPos = endPos;
            buffer = "";
          }
        }
      }

      // Flush remaining buffer
      if (buffer.trim() && !signal.aborted) {
        const spanId = nextSpanId();
        yield { type: "append", span: { id: spanId, layer: "fluid", text: buffer, startPos, endPos: startPos + buffer.length } };
        yield { type: "lock", spanId };
      }

      // Record chat span
      const chatLatency = performance.now() - chatTTFT;
      this.tracer?.recordChat(
        this.fastProvider.model ?? "unknown",
        { totalTokens: 0 },
        ttftMs, chatLatency,
      );

      if (signal.aborted) return;

      // Tool calls?
      const toolCalls = lastToken.toolCalls;
      if (!toolCalls || toolCalls.length === 0) break;
      if (!this.toolRegistry) break;

      const assistantMsg: any = { role: "assistant", content: null };
      if (lastToken.reasoningContent) assistantMsg.reasoning_content = lastToken.reasoningContent;
      assistantMsg.tool_calls = toolCalls.map((tc: ToolCall) => ({
        id: tc.id, type: "function", function: { name: tc.name, arguments: JSON.stringify(tc.arguments) },
      }));
      messages.push(assistantMsg);

      for (const tc of toolCalls) {
        const toolStart = performance.now();
        const result = await this.toolRegistry.execute(tc.name, tc.arguments, {
          workingDir: process.cwd(), sessionId: "",
        });
        const toolDur = performance.now() - toolStart;
        this.tracer?.recordToolCall(tc.name, tc.arguments, {
          success: result.success,
          output: result.output,
          error: result.error,
        }, toolDur, result.truncated);
        messages.push({ role: "tool", tool_call_id: tc.id, content: result.output });
        const toolSpanId = nextSpanId();
        const preview = (result.output ?? result.error ?? "").slice(0, 200);
        yield { type: "append", span: { id: toolSpanId, layer: "locked", text: `[${tc.name}] ${preview}`, startPos: 0, endPos: 0, committedAt: Date.now() } };
      }
    }
  }
}
