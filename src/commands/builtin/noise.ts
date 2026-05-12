import type { LocalCommand, CommandContext } from "../types";

export const noiseCommand: LocalCommand = {
  type: "local",
  name: "noise",
  description: "Show current context noise ratio",
  aliases: ["n"],
  call(_args: string, ctx: CommandContext) {
    const agent = ctx.agent;
    if (!agent.contextNoiseDetector) {
      return "Noise detector not initialized.";
    }
    const report = agent.contextNoiseDetector.lastReport;
    if (!report) {
      return "No noise data yet. Send a message first.";
    }
    return agent.contextNoiseDetector.formatReport(report);
  },
};
