/** Keybinding types — copied from Claude Code src/keybindings/types.ts */

export interface ParsedKeystroke {
  key: string;
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
  super: boolean;
}

export interface ParsedChord {
  keystrokes: ParsedKeystroke[];
}

export type KeyAction = string; // e.g., "app:interrupt", "history:search"

export interface ParsedBinding {
  chord: ParsedChord;
  action: KeyAction;
  context: string;
}

export type KeybindingContextName = "global" | "input" | "search" | "confirmation";

export interface KeybindingBlock {
  context: KeybindingContextName;
  bindings: Record<string, KeyAction>; // e.g., { "ctrl+c": "app:interrupt" }
}
