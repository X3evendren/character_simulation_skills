/**
 * Command system — register builtins + export public API.
 */
import { registerCommand } from "./registry";
import { router } from "./router";
import { helpCommand } from "./builtin/help";
import { quitCommand } from "./builtin/quit";
import { statsCommand } from "./builtin/stats";
import { modelCommand } from "./builtin/model";
import { dreamCommand } from "./builtin/dream";
import { oathCommand } from "./builtin/oath";
import { thinkCommand } from "./builtin/think";

export function registerBuiltinCommands(): void {
  // Priority commands (execute outside turn lock)
  router.setPriority("quit");
  router.setPriority("exit");
  router.setPriority("q");

  // Register all commands
  registerCommand(quitCommand);
  registerCommand(helpCommand);
  registerCommand(statsCommand);
  registerCommand(modelCommand);
  registerCommand(dreamCommand);
  registerCommand(oathCommand);
  registerCommand(thinkCommand);
}

// Public API
export { getCommands, findCommand, getCommandNames } from "./registry";
export { CommandRouter, router } from "./router";
export { parseSlashCommand, isCommandInput } from "./parser";
export type { Command, CommandContext, LocalCommand, PromptCommand } from "./types";
