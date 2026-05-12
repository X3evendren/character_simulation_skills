import type { LocalCommand, CommandContext } from "../types";
import { getCommands } from "../registry";

export const helpCommand: LocalCommand = {
  type: "local",
  name: "help",
  description: "Show help and available commands",
  aliases: ["h", "?"],
  call(_args: string, ctx: CommandContext) {
    const cmds = getCommands(ctx);
    const lines: string[] = [];
    lines.push("Commands:");
    for (const cmd of cmds) {
      const aliases = cmd.aliases?.length ? ` (${cmd.aliases.join(", ")})` : "";
      lines.push(`  /${cmd.name}${aliases} — ${cmd.description}`);
    }
    lines.push("");
    lines.push("Input modes:");
    lines.push("  /command  — slash command");
    lines.push("  !command  — execute shell command");
    lines.push("  text      — talk to " + ctx.agent.config.name);
    lines.push("");
    lines.push("Keys:");
    lines.push("  Ctrl+C    — interrupt");
    lines.push("  Ctrl+D    — quit");
    lines.push("  Ctrl+L    — clear screen");
    lines.push("  Ctrl+R    — search history");
    lines.push("  Up/Down   — navigate history");
    lines.push("  Tab       — complete command");
    return lines.join("\n");
  },
};
