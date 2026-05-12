/**
 * Command Router — 4-layer dispatch copied from nanobot command/router.py
 *
 * Layers (highest priority first):
 *   1. priority  — execute outside turn lock (e.g., /quit, /stop)
 *   2. exact     — exact name match
 *   3. prefix    — longest prefix match (supports "/dream --full")
 *   4. interceptor — fallback handler for unmatched input
 */
import type { Command, CommandContext, LocalCommand, PromptCommand } from "./types";
import { findCommand, getCommands } from "./registry";
import { isCommandInput, parseSlashCommand } from "./parser";

export interface RouterResult {
  type: "local" | "prompt" | "unknown";
  output?: string;          // For local commands
  promptText?: string;      // For prompt commands (injected into LLM prompt)
  commandName?: string;
}

export class CommandRouter {
  private priorityNames: Set<string> = new Set();
  private interceptors: Array<(input: string, ctx: CommandContext) => RouterResult | null> = [];

  /** Register a command name as priority (executes outside turn lock) */
  setPriority(name: string): void {
    this.priorityNames.add(name);
  }

  /** Add a fallback interceptor */
  addInterceptor(fn: (input: string, ctx: CommandContext) => RouterResult | null): void {
    this.interceptors.push(fn);
  }

  isPriorityCommand(input: string): boolean {
    if (!isCommandInput(input)) return false;
    const parsed = parseSlashCommand(input);
    return parsed ? this.priorityNames.has(parsed.name) : false;
  }

  /**
   * Dispatch: priority → exact → prefix → interceptor
   * Returns RouterResult with output for local commands or promptText for prompt commands.
   */
  async dispatch(input: string, ctx: CommandContext): Promise<RouterResult> {
    if (!isCommandInput(input)) {
      return { type: "unknown" };
    }

    const parsed = parseSlashCommand(input);
    if (!parsed) {
      return { type: "unknown" };
    }

    // Layer 1: Exact match
    const cmd = findCommand(parsed.name);
    if (cmd) {
      return this.executeCommand(cmd, parsed.args, ctx);
    }

    // Layer 2: Prefix match (longest match first)
    const allCmds = getCommands(ctx);
    const prefixMatches = allCmds
      .filter(c => parsed.name.startsWith(c.name) || c.aliases?.some(a => parsed.name.startsWith(a)))
      .sort((a, b) => b.name.length - a.name.length);

    if (prefixMatches.length > 0) {
      return this.executeCommand(prefixMatches[0], parsed.args, ctx);
    }

    // Layer 3: Interceptors
    for (const interceptor of this.interceptors) {
      const result = interceptor(input, ctx);
      if (result) return result;
    }

    return {
      type: "unknown",
      output: `Unknown command: /${parsed.name}\nType /help to see available commands.`,
    };
  }

  /**
   * Dispatch a priority command (outside turn lock). Only local commands with immediate:true.
   */
  async dispatchPriority(input: string, ctx: CommandContext): Promise<RouterResult> {
    if (!isCommandInput(input)) return { type: "unknown" };

    const parsed = parseSlashCommand(input);
    if (!parsed || !this.priorityNames.has(parsed.name)) {
      return { type: "unknown" };
    }

    const cmd = findCommand(parsed.name);
    if (cmd && cmd.type === "local") {
      return this.executeCommand(cmd, parsed.args, ctx);
    }

    return { type: "unknown" };
  }

  private async executeCommand(cmd: Command, args: string, ctx: CommandContext): Promise<RouterResult> {
    if (cmd.type === "local") {
      const output = await cmd.call(args, ctx);
      return { type: "local", output: output ?? "", commandName: cmd.name };
    }
    if (cmd.type === "prompt") {
      const promptText = cmd.getPromptForCommand(args, ctx);
      return { type: "prompt", promptText, commandName: cmd.name };
    }
    return { type: "unknown" };
  }
}

/** Singleton router instance */
export const router = new CommandRouter();
