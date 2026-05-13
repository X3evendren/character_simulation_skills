import type { LocalCommand, CommandContext } from "../types";
import { PROVIDERS } from "../../agent/provider-registry";

export const modelCommand: LocalCommand = {
  type: "local",
  name: "model",
  description: "Show or switch the current model",
  aliases: ["m"],
  call(args: string, _ctx: CommandContext) {
    if (!args) {
      return "Current: deepseek-v4-pro (gen) / deepseek-v4-flash (psych)\n\nAvailable providers:\n" +
        PROVIDERS.map(p => `  ${p.name.padEnd(14)} — ${p.defaultApiBase}`).join("\n");
    }
    return `Model switching via /model is not yet implemented. Requested: ${args}`;
  },
};
