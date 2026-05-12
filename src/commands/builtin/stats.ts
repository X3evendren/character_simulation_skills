import type { LocalCommand, CommandContext } from "../types";

export const statsCommand: LocalCommand = {
  type: "local",
  name: "stats",
  description: "Show psychological state and parameters",
  aliases: ["st"],
  call(_args: string, ctx: CommandContext) {
    const a = ctx.agent;
    const lines: string[] = [];
    lines.push("═".repeat(28));
    lines.push(`  Saturation: ${a.saturation.s.toFixed(3)}`);
    lines.push(`  Oath: ${a.loveMetrics.gottmanStatus} · assurance=${a.loveMetrics.assurance}`);
    lines.push(`  Drives: ${Object.entries(a.drives.getDriveVector()).map(([k, v]) => `${k}=${v.toFixed(2)}`).join(", ")}`);
    lines.push(`  Tick: ${a.tickCount} · Turn: ${a.turnCount}`);
    lines.push("─".repeat(28));
    lines.push("  Top parameters:");
    const snap = a.params.snapshot();
    const top = Object.entries(snap as Record<string, number>)
      .filter(([, v]) => Math.abs(v) > 0.1)
      .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
      .slice(0, 10)
      .map(([k, v]) => `  ${k.padEnd(22)} ${v > 0 ? "+" : ""}${v}`);
    lines.push(top.join("\n"));
    return lines.join("\n");
  },
};
