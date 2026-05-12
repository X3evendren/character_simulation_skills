import type { LocalCommand, CommandContext } from "../types";

export const quitCommand: LocalCommand = {
  type: "local",
  name: "quit",
  description: "Exit Character Mind",
  aliases: ["exit", "q"],
  immediate: true,
  async call(_args: string, ctx: CommandContext) {
    await ctx.agent.shutdown();
    process.exit(0);
  },
};
