/** Keybinding parser — copied from Claude Code src/keybindings/parser.ts */

import type { ParsedKeystroke, ParsedChord, ParsedBinding, KeybindingBlock, KeyAction } from "./types";

const MODIFIER_ALIASES: Record<string, string> = {
  ctrl: "ctrl", control: "ctrl",
  alt: "alt", opt: "alt", option: "alt",
  shift: "shift",
  meta: "meta", cmd: "meta", command: "meta", super: "super", win: "super",
};

const MODIFIER_NAMES = new Set(["ctrl", "alt", "shift", "meta", "super"]);

/** Parse "ctrl+c" or "ctrl+shift+k" into ParsedKeystroke */
export function parseKeystroke(input: string): ParsedKeystroke | null {
  const parts = input.toLowerCase().split("+");
  const result: ParsedKeystroke = {
    key: "", ctrl: false, alt: false, shift: false, meta: false, super: false,
  };

  for (const part of parts) {
    const normalized = MODIFIER_ALIASES[part.trim()] ?? part.trim();
    if (MODIFIER_NAMES.has(normalized)) {
      (result as any)[normalized] = true;
    } else {
      if (result.key) return null; // multiple non-modifier keys
      result.key = normalized;
    }
  }

  if (!result.key) {
    // Handle special cases like "ctrl" alone
    if (result.ctrl) result.key = "ctrl";
    else return null;
  }

  return result;
}

/** Parse "ctrl+x ctrl+k" into ParsedChord */
export function parseChord(input: string): ParsedChord | null {
  const parts = input.trim().split(/\s+/);
  const keystrokes: ParsedKeystroke[] = [];
  for (const part of parts) {
    const ks = parseKeystroke(part);
    if (!ks) return null;
    keystrokes.push(ks);
  }
  return keystrokes.length > 0 ? { keystrokes } : null;
}

/** Parse KeybindingBlock[] into flat ParsedBinding[] */
export function parseBindings(blocks: KeybindingBlock[]): ParsedBinding[] {
  const result: ParsedBinding[] = [];
  for (const block of blocks) {
    for (const [keyCombo, action] of Object.entries(block.bindings)) {
      const chord = parseChord(keyCombo);
      if (chord) {
        result.push({ chord, action, context: block.context });
      }
    }
  }
  return result;
}
