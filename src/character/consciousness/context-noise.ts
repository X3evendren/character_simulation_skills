/** Context Noise Detector — measure prompt token distribution, detect noise overload.
 *
 *  Hermes pattern: ask the agent "how noisy is your context right now?"
 *  When one section dominates (>40%), the agent loses attention focus.
 */

export interface NoiseSection {
  name: string;
  tokens: number;
  percentage: number;
}

export interface NoiseReport {
  sections: NoiseSection[];
  totalTokens: number;
  noiseRatio: string; // "low" | "medium" | "high" | "critical"
  warnings: string[];
}

const SECTION_THRESHOLD = 0.40; // single section > 40% → warning
const TOTAL_WARN = 3000;       // total tokens > 3k → consider compression
const TOTAL_CRITICAL = 5000;   // total tokens > 5k → must compress

export class ContextNoiseDetector {
  private history: NoiseReport[] = [];

  /** Analyze a prompt by text length (proxy for token count). */
  analyze(sections: Record<string, string>): NoiseReport {
    const entries: NoiseSection[] = [];
    let total = 0;

    for (const [name, text] of Object.entries(sections)) {
      const tokens = Math.round(text.length / 3.5); // rough char→token estimate for Chinese
      entries.push({ name, tokens, percentage: 0 });
      total += tokens;
    }

    for (const e of entries) {
      e.percentage = total > 0 ? Math.round((e.tokens / total) * 100) : 0;
    }

    const warnings: string[] = [];
    for (const e of entries) {
      if (e.percentage > SECTION_THRESHOLD * 100) {
        warnings.push(`${e.name} 占 ${e.percentage}%，超过阈值，可能导致注意力偏向`);
      }
    }

    let noiseRatio: string;
    if (total > TOTAL_CRITICAL) noiseRatio = "critical";
    else if (total > TOTAL_WARN) noiseRatio = "high";
    else if (warnings.length > 0) noiseRatio = "medium";
    else noiseRatio = "low";

    if (total > TOTAL_WARN) {
      warnings.push(`总 prompt 约 ${total} tokens，建议压缩记忆或上下文`);
    }

    const report: NoiseReport = { sections: entries, totalTokens: total, noiseRatio, warnings };
    this.history.push(report);
    if (this.history.length > 100) this.history = this.history.slice(-100);

    return report;
  }

  /** Format a human-readable noise report for /noise command. */
  formatReport(report: NoiseReport): string {
    const lines: string[] = [];
    lines.push(`噪音比: ${report.noiseRatio}  (约 ${report.totalTokens} tokens)`);
    lines.push("");
    for (const s of report.sections) {
      const bar = "█".repeat(Math.round(s.percentage / 5));
      lines.push(`  ${s.name.padEnd(12)} ${bar.padEnd(20)} ${s.percentage}%`);
    }
    if (report.warnings.length) {
      lines.push("");
      for (const w of report.warnings) lines.push(`  ⚠ ${w}`);
    }
    return lines.join("\n");
  }

  /** Get the latest noise report. */
  get lastReport(): NoiseReport | null {
    return this.history.length > 0 ? this.history[this.history.length - 1] : null;
  }

  /** Average noise ratio over last N reports. */
  averageNoise(n = 10): string {
    const recent = this.history.slice(-n);
    if (!recent.length) return "unknown";
    const counts = { low: 0, medium: 0, high: 0, critical: 0 };
    for (const r of recent) {
      counts[r.noiseRatio]++;
    }
    if (counts.critical > 0) return "critical";
    if (counts.high > recent.length * 0.3) return "high";
    if (counts.medium > recent.length * 0.5) return "medium";
    return "low";
  }
}
