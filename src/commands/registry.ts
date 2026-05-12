/**
 * Command Registry — Static import → COMMANDS array, copied from Claude Code src/commands.ts
 * Supports multi-source merging and linear find-by-name/alias.
 */
import type { Command, CommandContext } from "./types";

/** All registered commands (built-in + plugin-added) */
const COMMANDS: Command[] = [];

/**
 * Register a command. Called by builtin/index.ts and plugins.
 */
export function registerCommand(cmd: Command): void {
  // Prevent duplicate names
  if (COMMANDS.some(c => c.name === cmd.name)) {
    throw new Error(`Command "${cmd.name}" already registered`);
  }
  COMMANDS.push(cmd);
}

/**
 * Get all registered commands, optionally filtered by enabled status.
 */
export function getCommands(ctx?: CommandContext): Command[] {
  if (!ctx) return [...COMMANDS];
  return COMMANDS.filter(cmd => {
    if (cmd.isHidden) return false;
    if (!cmd.isEnabled) return true;
    return cmd.isEnabled(ctx);
  });
}

/**
 * Find a command by name or alias. Linear search (same as Claude Code findCommand).
 */
export function findCommand(name: string): Command | undefined {
  const lower = name.toLowerCase();
  return COMMANDS.find(cmd => {
    if (cmd.name === lower) return true;
    if (cmd.aliases?.some(a => a.toLowerCase() === lower)) return true;
    return false;
  });
}

/**
 * Get command names for tab completion.
 */
export function getCommandNames(): string[] {
  return COMMANDS.filter(c => !c.isHidden).map(c => c.name);
}
