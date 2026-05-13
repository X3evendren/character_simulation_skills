/**
 * Eval Reporters — Console, JSON, Markdown output formatters.
 */
import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import type { SuiteResult, CaseResult } from "./runner";

export class ConsoleReporter {
  report(suite: SuiteResult): void {
    const { total, passed, failed, avgScore, cases, elapsedMs } = suite;

    console.log(`\n${"=".repeat(60)}`);
    console.log(`Eval Results: ${passed}/${total} passed (${avgScore}%) · ${(elapsedMs / 1000).toFixed(1)}s`);
    console.log(`${"=".repeat(60)}\n`);

    for (const c of cases) {
      const icon = c.passed ? "✓" : "✗";
      const scorePct = c.maxScore > 0 ? (c.score / c.maxScore * 100).toFixed(0) : "0";
      console.log(`  ${icon} ${c.caseId} [${scorePct}%]`);
      if (c.error) {
        console.log(`    Error: ${c.error}`);
      }
      for (const d of c.details) {
        if (!d.passed) {
          console.log(`    ✗ ${d.behavior} → ${d.actual}`);
        }
      }
    }

    if (failed > 0) {
      console.log(`\n  ${failed} case(s) failed.`);
    } else {
      console.log(`\n  All ${total} cases passed.`);
    }
  }
}

export class JsonReporter {
  private dir: string;

  constructor(dir?: string) {
    this.dir = dir ?? join(process.cwd(), "eval", "results");
  }

  report(suite: SuiteResult, label?: string): void {
    if (!existsSync(this.dir)) mkdirSync(this.dir, { recursive: true });
    const name = label ?? `eval_${Date.now()}`;
    writeFileSync(join(this.dir, `${name}.json`), JSON.stringify(suite, null, 2), "utf-8");
  }
}

export class MarkdownReporter {
  private dir: string;

  constructor(dir?: string) {
    this.dir = dir ?? join(process.cwd(), "eval", "results");
  }

  report(suite: SuiteResult, label?: string): void {
    if (!existsSync(this.dir)) mkdirSync(this.dir, { recursive: true });
    const name = label ?? `report_${Date.now()}`;
    const lines: string[] = [];

    lines.push("# Eval Report\n");
    lines.push(`**${suite.passed}/${suite.total}** passed · **${suite.avgScore}%** · ${(suite.elapsedMs / 1000).toFixed(1)}s\n`);
    lines.push("| Case | Result | Score | Details |");
    lines.push("|------|--------|-------|---------|");

    for (const c of suite.cases) {
      const icon = c.passed ? "✓" : "✗";
      const fails = c.details.filter(d => !d.passed).map(d => d.behavior).join(", ");
      lines.push(`| ${c.caseId} | ${icon} | ${c.maxScore > 0 ? (c.score / c.maxScore * 100).toFixed(0) : 0}% | ${fails || "—"} |`);
    }

    writeFileSync(join(this.dir, `${name}.md`), lines.join("\n"), "utf-8");
  }
}
