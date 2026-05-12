import type { LocalCommand, CommandContext } from "../types";

export const oathCommand: LocalCommand = {
  type: "local",
  name: "oath",
  description: "Show oath/vow state and love metrics",
  aliases: ["love"],
  call(_args: string, ctx: CommandContext) {
    const a = ctx.agent;
    const lines: string[] = [];
    lines.push("═".repeat(28));
    lines.push("  Oath Store");
    const oathStats = a.oathStore.stats();
    lines.push(`  Total: ${oathStats.total} · Active: ${oathStats.active} · Lapsing: ${oathStats.lapsing} · Broken: ${oathStats.broken} · Repaired: ${oathStats.repaired}`);
    lines.push("");
    lines.push("  Love Metrics");
    const lm = a.loveMetrics;
    lines.push(`  Assurance: ${lm.assurance}`);
    lines.push(`  Gottman: ${lm.gottmanStatus} · P/N Ratio: ${lm.positiveRatio.toFixed(1)}`);
    lines.push(`  Duration: ${lm.relationshipDurationDays.toFixed(0)}d · Depth: ${lm.depthSessions}`);
    lines.push(`  Ruptures: ${lm.ruptureCount} · Repairs: ${lm.repairCount}`);
    lines.push("");
    lines.push("  Irreducible Prior");
    const ip = a.irreduciblePrior;
    lines.push(`  Active: ${ip.isActive} · Gamma: ${ip.gamma}`);
    lines.push(`  KL Est: ${ip.currentKL.toFixed(4)} · Violations: ${ip.violationCount}`);
    lines.push("");
    lines.push("  Saturation");
    lines.push(`  Mode: ${a.saturationDetector.mode} · Level: ${a.saturationDetector.saturationLevel.toFixed(3)}`);
    lines.push(`  Precision Threat: ${a.continuousParams.precisionThreat.toFixed(3)}`);
    lines.push(`  Precision Safety: ${a.continuousParams.precisionSafety.toFixed(3)}`);
    return lines.join("\n");
  },
};
