/** Tool result persistence — large results → disk, LLM gets preview. */

import { mkdirSync, writeFileSync, existsSync } from "fs";
import { join, resolve } from "path";

const MAX_INLINE_CHARS = 50000; // 50KB inline, larger → persist
const PREVIEW_CHARS = 2000;

export class ResultStorage {
  private storageDir: string;

  constructor(baseDir: string) {
    this.storageDir = resolve(baseDir, "tool-results");
    if (!existsSync(this.storageDir)) {
      mkdirSync(this.storageDir, { recursive: true });
    }
  }

  /** Process a tool result: if too large, persist to disk and return preview. */
  process(toolUseId: string, output: string, toolName: string): string {
    if (!output) return `(${toolName} completed with no output)`;

    if (output.length <= MAX_INLINE_CHARS) return output;

    // Persist to disk
    const filename = `${toolUseId}.txt`;
    const filepath = join(this.storageDir, filename);
    writeFileSync(filepath, output, "utf-8");

    const preview = output.slice(0, PREVIEW_CHARS);
    const sizeKB = (output.length / 1024).toFixed(1);
    return [
      `[persisted] Output too large (${sizeKB} KB). Full output saved to: ${filepath}`,
      "",
      `Preview (first ${PREVIEW_CHARS} chars):`,
      preview,
      `... (${output.length - PREVIEW_CHARS} more chars)`,
    ].join("\n");
  }

  /** Read a persisted result back. */
  read(toolUseId: string): string | null {
    try {
      const { readFileSync } = require("fs");
      return readFileSync(join(this.storageDir, `${toolUseId}.txt`), "utf-8");
    } catch {
      return null;
    }
  }
}

/** Micro-compaction: truncate old large tool results to save token budget.
 *  Keep last 10 results full, older ones cut to 200 chars. */
export function microCompact(results: Array<{ id: string; output: string }>): Array<{ id: string; output: string }> {
  const threshold = 500;
  return results.map((r, i) => {
    if (i < results.length - 10) return r; // keep recent 10
    if (r.output.length <= threshold) return r;
    return { id: r.id, output: `[omitted: ${r.output.length} chars from earlier tool result]` };
  });
}
