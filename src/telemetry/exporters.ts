/**
 * Span Exporters — JSONL file writer + Console debug writer.
 * Both implement the SpanExporter interface so they can be swapped transparently.
 */
import { writeFileSync, appendFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import type { CompletedSpan, SpanExporter } from "./tracer";

/** Write spans to trace-data/YYYY-MM-DD-HH.jsonl */
export class JsonlExporter implements SpanExporter {
  private dir: string;
  private currentFile = "";
  private currentHour = "";

  constructor(dir?: string) {
    this.dir = dir ?? join(process.cwd(), "trace-data");
  }

  export(span: CompletedSpan): void {
    if (!existsSync(this.dir)) mkdirSync(this.dir, { recursive: true });
    const hour = this._hourKey();
    if (hour !== this.currentHour) {
      this.currentHour = hour;
      this.currentFile = join(this.dir, `${this._dateKey()}-${hour}.jsonl`);
    }
    appendFileSync(this.currentFile, JSON.stringify(span) + "\n", "utf-8");
  }

  async flush(): Promise<void> { /* no buffering */ }
  async shutdown(): Promise<void> { /* no-op */ }

  private _dateKey(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }
  private _hourKey(): string {
    return String(new Date().getHours()).padStart(2, "0");
  }
}

/** Write spans to stderr for development. Enabled via TRACE_CONSOLE=1 env. */
export class ConsoleExporter implements SpanExporter {
  private enabled: boolean;

  constructor() {
    this.enabled = process.env.TRACE_CONSOLE === "1";
  }

  export(span: CompletedSpan): void {
    if (!this.enabled) return;
    const indent = span.parentSpanId ? "  " : "";
    const dur = ((span.endTime - span.startTime)).toFixed(1);
    const status = span.status === "error" ? " ✗" : "";
    process.stderr.write(`${indent}[trace] ${span.name} (${dur}ms)${status}\n`);
  }

  async flush(): Promise<void> { /* no-op */ }
  async shutdown(): Promise<void> { /* no-op */ }
}

/** Composite exporter: fan-out to multiple exporters. */
export class CompositeExporter implements SpanExporter {
  private exporters: SpanExporter[];

  constructor(...exporters: SpanExporter[]) {
    this.exporters = exporters;
  }

  export(span: CompletedSpan): void {
    for (const e of this.exporters) e.export(span);
  }

  async flush(): Promise<void> {
    await Promise.all(this.exporters.map(e => e.flush()));
  }

  async shutdown(): Promise<void> {
    await Promise.all(this.exporters.map(e => e.shutdown()));
  }
}
