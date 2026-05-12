/** Streaming Tool Executor — parallel read-only tools, serial write tools. */

import type { ToolDef, ToolResult, ToolContext } from "./types";
import type { ToolRegistry } from "./registry";

interface QueuedTool {
  id: string;
  name: string;
  params: any;
  isSafe: boolean;
  status: "queued" | "running" | "completed" | "yielded";
  result: ToolResult | null;
  startedAt: number;
}

export class StreamingToolExecutor {
  private registry: ToolRegistry;
  private ctx: ToolContext;
  private queue: QueuedTool[] = [];
  private maxConcurrent = 10;

  constructor(registry: ToolRegistry, ctx: ToolContext) {
    this.registry = registry;
    this.ctx = ctx;
  }

  /** Add a tool call from the stream. Non-blocking. */
  addTool(id: string, name: string, params: any): void {
    const tool = this.registry.get(name);
    const isSafe = tool?.isConcurrencySafe ?? false;
    this.queue.push({
      id, name, params, isSafe, status: "queued", result: null, startedAt: Date.now(),
    });
    // Kick off non-blocking execution
    this._processQueue();
  }

  /** Get results for tools that have completed (non-blocking). */
  getCompletedResults(): Array<{ id: string; result: ToolResult }> {
    const completed: Array<{ id: string; result: ToolResult }> = [];
    for (const t of this.queue) {
      if (t.status === "completed" && t.result) {
        completed.push({ id: t.id, result: t.result });
        t.status = "yielded";
      }
    }
    return completed;
  }

  /** Wait for all remaining tools to complete. */
  async getRemainingResults(): Promise<Array<{ id: string; result: ToolResult }>> {
    while (this.queue.some(t => t.status === "queued" || t.status === "running")) {
      await new Promise(r => setTimeout(r, 50));
    }
    return this.getCompletedResults();
  }

  /** Abandon all pending tools. */
  discard(): void {
    for (const t of this.queue) {
      if (t.status === "queued") t.status = "completed";
    }
  }

  private _processQueue(): void {
    for (const t of this.queue) {
      if (t.status !== "queued") continue;

      if (this._canExecute(t.isSafe)) {
        t.status = "running";
        this._executeOne(t);
      } else if (!t.isSafe) {
        // Non-safe tool: wait until no other tools are running
        break;
      }
    }
  }

  private _canExecute(isSafe: boolean): boolean {
    if (isSafe) {
      // Safe tools: up to maxConcurrent
      const running = this.queue.filter(t => t.status === "running").length;
      return running < this.maxConcurrent;
    }
    // Non-safe: only if nothing else is running
    return !this.queue.some(t => t.status === "running");
  }

  private async _executeOne(tool: QueuedTool): Promise<void> {
    try {
      tool.result = await this.registry.execute(tool.name, tool.params, this.ctx);
    } catch (e: any) {
      tool.result = { success: false, error: e.message, output: `Error: ${e.message}`, truncated: false };
    }
    tool.status = "completed";
    // Kick off next in queue
    this._processQueue();
  }
}
