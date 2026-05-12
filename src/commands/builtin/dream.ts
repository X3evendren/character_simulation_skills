import type { LocalCommand, CommandContext } from "../types";

export const dreamCommand: LocalCommand = {
  type: "local",
  name: "dream",
  description: "Trigger memory sleep cycle (daydream / quick / full)",
  aliases: ["sleep"],
  async call(args: string, ctx: CommandContext) {
    const a = ctx.agent;
    if (args === "--full" || args === "-f") {
      const report = await a.metabolism.fullSleep();
      return `Full sleep complete.\n  Promoted: ${report.promoted}\n  Merged: ${report.merged}\n  Archived: ${report.archived}\n  Conflicts: ${report.conflicts}`;
    }
    if (args === "--quick" || args === "-q") {
      const report = await a.metabolism.quickSleep();
      return `Quick sleep complete.\n  Promoted: ${report.promoted}\n  Merged: ${report.merged}`;
    }
    // Default: daydream
    const report = await a.metabolism.daydream();
    return `Daydream complete.\n  Merged: ${report.merged}`;
  },
};
