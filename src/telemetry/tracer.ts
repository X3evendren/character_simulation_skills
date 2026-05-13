/**
 * Tracer — Lightweight span-based tracing for Agent operations.
 * Zero external dependencies. Uses crypto.randomUUID() + performance.now().
 *
 * Span hierarchy follows OTel GenAI semantic conventions:
 *   turn > { chat, cold_path, execute_tool }
 *
 * Tracer is always optional — all calls use `?.` so no overhead when absent.
 */
import { randomUUID } from "crypto";

export type SpanStatus = "ok" | "error";

export interface CompletedSpan {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  name: string;
  startTime: number;
  endTime: number;
  status: SpanStatus;
  attributes: Record<string, unknown>;
}

export interface Span {
  readonly spanId: string;
  readonly traceId: string;
  readonly parentSpanId?: string;
  readonly name: string;
  readonly startTime: number;
  setStatus(status: SpanStatus): void;
  setAttribute(key: string, value: unknown): void;
  /** Called by Tracer.endSpan() — don't call directly */
  _finish(endTime: number): CompletedSpan;
}

export interface SpanExporter {
  export(span: CompletedSpan): void;
  flush(): Promise<void>;
  shutdown(): Promise<void>;
}

class SpanImpl implements Span {
  spanId = randomUUID();
  startTime = performance.now();
  private _status: SpanStatus = "ok";
  private _attrs: Record<string, unknown> = {};

  constructor(
    readonly traceId: string,
    readonly name: string,
    readonly parentSpanId?: string,
  ) {}

  setStatus(s: SpanStatus) { this._status = s; }
  setAttribute(key: string, value: unknown) { this._attrs[key] = value; }

  _finish(endTime: number): CompletedSpan {
    return {
      traceId: this.traceId,
      spanId: this.spanId,
      parentSpanId: this.parentSpanId,
      name: this.name,
      startTime: this.startTime,
      endTime,
      status: this._status,
      attributes: this._attrs,
    };
  }
}

export class Tracer {
  private traceId = "";
  private spanStack: SpanImpl[] = [];
  private exporter: SpanExporter;

  constructor(exporter: SpanExporter) {
    this.exporter = exporter;
  }

  /** Start a new trace (top-level, e.g. for a user turn) */
  startTrace(): string {
    this.traceId = randomUUID();
    return this.traceId;
  }

  /** Start a named span. If no trace active, auto-creates one. */
  startSpan(name: string, attrs?: Record<string, unknown>): Span {
    if (!this.traceId) this.startTrace();
    const parent = this.spanStack.length > 0 ? this.spanStack[this.spanStack.length - 1] : undefined;
    const span = new SpanImpl(this.traceId, name, parent?.spanId);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) span.setAttribute(k, v);
    }
    this.spanStack.push(span);
    return span;
  }

  /** End a span. Spans should be ended in LIFO order. */
  endSpan(span: Span): void {
    const idx = this.spanStack.findIndex(s => s.spanId === span.spanId);
    if (idx < 0) return;
    // End all nested spans first
    while (this.spanStack.length > idx + 1) {
      const child = this.spanStack.pop()!;
      child.setStatus("error");
      child.setAttribute("_unclosed", true);
      const completed = child._finish(performance.now());
      this.exporter.export(completed);
    }
    const target = this.spanStack.pop()!;
    const completed = target._finish(performance.now());
    this.exporter.export(completed);
  }

  /** Convenience: record a completed tool call */
  recordToolCall(name: string, args: Record<string, unknown>, result: { success: boolean; output?: string; error?: string }, durationMs: number, truncated = false): void {
    const span = this.startSpan("execute_tool", {
      "gen_ai.tool.name": name,
      "gen_ai.tool.call.arguments": JSON.stringify(args).slice(0, 500),
    });
    span.setAttribute("gen_ai.tool.call.success", result.success);
    span.setAttribute("gen_ai.tool.call.duration_ms", durationMs);
    span.setAttribute("gen_ai.tool.result.truncated", truncated);
    if (result.output) {
      span.setAttribute("gen_ai.tool.call.result", result.output.slice(0, 300));
      span.setAttribute("gen_ai.tool.result.length", result.output.length);
    }
    if (result.error) span.setAttribute("gen_ai.tool.call.error", result.error);
    if (!result.success) span.setStatus("error");
    // Override timing since we know the actual duration
    const now = performance.now();
    const fakeSpan = span as unknown as SpanImpl;
    // We need the actual span impl to set endTime correctly. Use setAttribute as workaround.
    span.setAttribute("_duration_override_ms", durationMs);
    this.endSpan(span);
  }

  /** Convenience: record a model chat call */
  recordChat(model: string, usage: { promptTokens?: number; completionTokens?: number; totalTokens?: number }, ttftMs: number, latencyMs: number, finishReason?: string): void {
    const span = this.startSpan("chat", {
      "gen_ai.request.model": model,
      "gen_ai.usage.input_tokens": usage.promptTokens ?? 0,
      "gen_ai.usage.output_tokens": usage.completionTokens ?? 0,
      "gen_ai.response.finish_reason": finishReason ?? "unknown",
    });
    span.setAttribute("ttft_ms", ttftMs);
    span.setAttribute("latency_ms", latencyMs);
    this.endSpan(span);
  }

  /** Convenience: start a turn span. Returns a cleanup function. */
  startTurn(input: string): Span {
    const s = this.startSpan("turn", {
      "gen_ai.user.input": input.slice(0, 500),
      "gen_ai.user.input.length": input.length,
    });
    this.startTrace(); // ensure fresh traceId per turn
    return s;
  }

  /** End a turn span */
  endTurn(span: Span, totalTokens?: number, turnCount?: number): void {
    if (totalTokens !== undefined) span.setAttribute("gen_ai.usage.total_tokens", totalTokens);
    if (turnCount !== undefined) span.setAttribute("turn.count", turnCount);
    this.endSpan(span);
  }

  async flush(): Promise<void> { await this.exporter.flush(); }
  async shutdown(): Promise<void> { await this.exporter.shutdown(); }
}
