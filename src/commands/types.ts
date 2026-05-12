/**
 * Command types — Discriminated union 
 * Supports PromptCommand (expands to prompt text) and LocalCommand (executes immediately).
 */
import type { CharacterAgent } from "../character/integration/character-agent";

export interface CommandContext {
  agent: CharacterAgent;
  args: string;           // Text after command name
  raw: string;            // Full user input including /
}

/** Expands to prompt text sent to LLM (e.g., /think I feel sad today) */
export interface PromptCommand {
  type: "prompt";
  name: string;
  description: string;
  aliases?: string[];
  isEnabled?: (ctx: CommandContext) => boolean;
  isHidden?: boolean;
  getPromptForCommand: (args: string, ctx: CommandContext) => string;
}

/** Executes immediately and returns a string to display (e.g., /stats, /quit) */
export interface LocalCommand {
  type: "local";
  name: string;
  description: string;
  aliases?: string[];
  isEnabled?: (ctx: CommandContext) => boolean;
  isHidden?: boolean;
  /** If true, executes outside the turn lock (for priority commands like /quit) */
  immediate?: boolean;
  call: (args: string, ctx: CommandContext) => string | Promise<string>;
}

export type Command = PromptCommand | LocalCommand;

export function isPromptCommand(cmd: Command): cmd is PromptCommand {
  return cmd.type === "prompt";
}

export function isLocalCommand(cmd: Command): cmd is LocalCommand {
  return cmd.type === "local";
}
