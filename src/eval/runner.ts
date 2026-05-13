/**
 * Eval Runner — Execute eval cases against the agent and produce results.
 */
import type { EvalCase, GoldenDataset } from "./golden-dataset";
import { scoreBehavior, type EvalAgentOutput } from "./scorers";

export interface CaseResult {
  caseId: string;
  passed: boolean;
  score: number;
  maxScore: number;
  details: Array<{ behavior: string; passed: boolean; actual: string; weight: number }>;
  response: string;
  totalTokens: number;
  error?: string;
}

export interface SuiteResult {
  total: number;
  passed: number;
  failed: number;
  avgScore: number;
  cases: CaseResult[];
  elapsedMs: number;
}

export interface EvalAgentAdapter {
  /** Run a single eval input and return the output. Suppresses UI. */
  evaluate(input: string): Promise<EvalAgentOutput>;
}

export class EvalRunner {
  private agent: EvalAgentAdapter;

  constructor(agent: EvalAgentAdapter) {
    this.agent = agent;
  }

  async runCase(evalCase: EvalCase): Promise<CaseResult> {
    try {
      const output = await this.agent.evaluate(evalCase.input);

      const details: CaseResult["details"] = [];
      let score = 0;
      let maxScore = 0;

      for (const behavior of evalCase.expectedBehaviors) {
        maxScore += behavior.weight;
        const result = scoreBehavior(output, behavior);
        score += result.score;
        details.push({
          behavior: `${behavior.type}: ${behavior.target}`,
          passed: result.passed,
          actual: result.actual,
          weight: behavior.weight,
        });
      }

      const passed = details.every(d => d.passed);
      return {
        caseId: evalCase.id,
        passed,
        score,
        maxScore,
        details,
        response: output.response.slice(0, 500),
        totalTokens: output.totalTokens,
      };
    } catch (e: any) {
      return {
        caseId: evalCase.id,
        passed: false,
        score: 0,
        maxScore: 1,
        details: [{ behavior: "error", passed: false, actual: e.message ?? "unknown error", weight: 1 }],
        response: "",
        totalTokens: 0,
        error: e.message,
      };
    }
  }

  async runSuite(dataset: GoldenDataset, opts?: { tags?: string[]; category?: string }): Promise<SuiteResult> {
    const cases = dataset.filter(opts ?? {});
    const start = Date.now();
    const results: CaseResult[] = [];

    for (const c of cases) {
      results.push(await this.runCase(c));
    }

    const passed = results.filter(r => r.passed).length;
    const avgScore = results.length > 0
      ? results.reduce((s, r) => s + (r.maxScore > 0 ? r.score / r.maxScore : 0), 0) / results.length
      : 1;

    return {
      total: results.length,
      passed,
      failed: results.length - passed,
      avgScore: +(avgScore * 100).toFixed(1),
      cases: results,
      elapsedMs: Date.now() - start,
    };
  }
}
