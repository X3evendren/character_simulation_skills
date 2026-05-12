/** Keybinding resolver with chord support — copied from Claude Code src/keybindings/resolver.ts */

import type { ParsedKeystroke, ParsedBinding, KeyAction, KeybindingContextName } from "./types";
import { parseBindings } from "./parser";
import { DEFAULT_BINDINGS } from "./defaults";

const CHORD_TIMEOUT = 1000; // ms

export interface ResolveResult {
  type: "match" | "none" | "chord_started" | "chord_cancelled";
  action?: KeyAction;
  pending?: ParsedBinding; // for chord_started
}

export class KeybindingResolver {
  private bindings: ParsedBinding[];
  private activeContexts: Set<KeybindingContextName> = new Set(["global", "input"]);

  constructor() {
    this.bindings = parseBindings(DEFAULT_BINDINGS);
  }

  setContext(name: KeybindingContextName, active: boolean): void {
    if (active) this.activeContexts.add(name);
    else this.activeContexts.delete(name);
  }

  /** Match a keystroke against bindings. Returns action if matched. */
  resolve(ks: ParsedKeystroke): ResolveResult {
    // Filter by active contexts, sorted by priority
    const candidates = this.bindings.filter(b =>
      this.activeContexts.has(b.context as KeybindingContextName)
    );

    // Try single-key match first
    for (const b of candidates) {
      if (b.chord.keystrokes.length === 1) {
        const bk = b.chord.keystrokes[0];
        if (bk.key === ks.key && bk.ctrl === ks.ctrl && bk.alt === ks.alt &&
            bk.shift === ks.shift && bk.meta === ks.meta && bk.super === ks.super) {
          return { type: "match", action: b.action };
        }
      }
    }

    // Check if any chord starts with this keystroke
    const chordCandidates = candidates.filter(
      b => b.chord.keystrokes.length > 1 && this._matchKeystroke(b.chord.keystrokes[0], ks)
    );
    if (chordCandidates.length > 0) {
      return { type: "chord_started", pending: chordCandidates[0] };
    }

    return { type: "none" };
  }

  /** Complete a chord by matching the second keystroke */
  completeChord(pending: ParsedBinding, ks: ParsedKeystroke): ResolveResult {
    if (pending.chord.keystrokes.length < 2) return { type: "none" };
    const target = pending.chord.keystrokes[1];
    if (this._matchKeystroke(target, ks)) {
      return { type: "match", action: pending.action };
    }
    return { type: "chord_cancelled" };
  }

  isEscapeCancel(ks: ParsedKeystroke): boolean {
    return ks.key === "escape" && !ks.ctrl && !ks.alt && !ks.meta;
  }

  private _matchKeystroke(a: ParsedKeystroke, b: ParsedKeystroke): boolean {
    return a.key === b.key && a.ctrl === b.ctrl && a.alt === b.alt &&
           a.shift === b.shift && a.meta === b.meta && a.super === b.super;
  }

  /** Get display text for reverse lookup (help) */
  getBindingForAction(action: KeyAction): string | undefined {
    const b = this.bindings.find(b => b.action === action);
    if (!b) return undefined;
    return b.chord.keystrokes.map(k => {
      const mods = [k.ctrl && "ctrl", k.alt && "alt", k.shift && "shift", k.meta && "meta"]
        .filter(Boolean).join("+");
      return mods ? `${mods}+${k.key}` : k.key;
    }).join(" ");
  }
}

export const keybindings = new KeybindingResolver();
