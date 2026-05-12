/** Default keybindings — copied from Claude Code src/keybindings/defaultBindings.ts */

import type { KeybindingBlock } from "./types";

export const DEFAULT_BINDINGS: KeybindingBlock[] = [
  {
    context: "global",
    bindings: {
      "ctrl+c": "app:interrupt",
      "ctrl+d": "app:exit",
      "ctrl+l": "app:redraw",
      "ctrl+r": "history:search",
    },
  },
  {
    context: "input",
    bindings: {
      "enter": "input:submit",
      "up": "history:previous",
      "down": "history:next",
      "tab": "input:complete",
      "escape": "input:cancel",
      "ctrl+u": "input:clearLine",
      "ctrl+a": "input:home",
      "ctrl+e": "input:end",
      "ctrl+k": "input:killLine",
      "ctrl+x ctrl+k": "app:forceStop",
    },
  },
  {
    context: "search",
    bindings: {
      "enter": "search:confirm",
      "escape": "search:cancel",
      "ctrl+c": "search:cancel",
      "up": "search:previous",
      "down": "search:next",
    },
  },
];
