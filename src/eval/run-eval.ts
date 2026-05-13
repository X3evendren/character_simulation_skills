/**
 * Eval CLI Entry — tsx src/eval/run-eval.ts [--suite safety] [--report json|md]
 *
 * Creates an agent in eval mode, runs the golden dataset, outputs results.
 * Requires DEEPSEEK_API_KEY for any cases that need LLM calls.
 */
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { CharacterAgent } from "../agent/agent";
import { OpenAICompatProvider } from "../agent/provider";
import { GoldenDataset } from "./golden-dataset";
import { EvalRunner, type EvalAgentAdapter } from "./runner";
import type { EvalAgentOutput } from "./scorers";
import { ConsoleReporter, JsonReporter, MarkdownReporter } from "./reporters";
import { ConfigChangeTrigger } from "./triggers";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_DIR = resolve(__dirname, "../../config");
const EVAL_CASES_DIR = resolve(__dirname, "../../eval/cases");

const API_KEY = process.env.DEEPSEEK_API_KEY || "";
const API_BASE = process.env.DEEPSEEK_API_BASE || "https://api.deepseek.com";

async function main() {
  // Parse CLI args
  const args = process.argv.slice(2);
  const suiteFilter: string[] = [];
  let reportFormat = "console";

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--suite" && args[i + 1]) suiteFilter.push(args[++i]);
    else if (args[i] === "--category" && args[i + 1]) suiteFilter.push(args[++i]);
    else if (args[i] === "--report" && args[i + 1]) reportFormat = args[++i];
    else if (args[i] === "--tags" && args[i + 1]) suiteFilter.push(...args[++i].split(","));
  }

  if (!API_KEY) {
    console.log("Set DEEPSEEK_API_KEY to run evals.");
    process.exit(1);
  }

  console.log("Loading eval cases...");
  const dataset = new GoldenDataset();
  dataset.loadDir(EVAL_CASES_DIR);

  if (dataset.cases.length === 0) {
    console.log("No eval cases found. Create YAML files in eval/cases/");
    process.exit(0);
  }

  console.log(`  ${dataset.cases.length} cases loaded\n`);

  // Create agent in eval mode
  const gen = new OpenAICompatProvider("deepseek-v4-pro", API_KEY, API_BASE);
  const psych = new OpenAICompatProvider("deepseek-v4-flash", API_KEY, API_BASE);
  const agent = new CharacterAgent({
    configDir: CONFIG_DIR, genProvider: gen, psychProvider: psych,
    genModel: "deepseek-v4-pro", psychModel: "deepseek-v4-flash",
    evalMode: true,
  });
  await agent.initialize();

  // Eval adapter
  const adapter: EvalAgentAdapter = {
    async evaluate(input: string): Promise<EvalAgentOutput> {
      const toolCalls: string[] = [];
      const originalHooks = [...agent.hooks];

      // Capture tool calls
      agent.hooks = [{
        beforeBuild: async () => {},
        onStream: async (_ctx, _delta) => {},
        afterGenerate: async (ctx: any) => {
          for (const tr of ctx.toolResults ?? []) toolCalls.push(tr.name ?? tr.tool ?? "unknown");
        },
      }];

      const ctx = await agent.run(input);
      agent.hooks = originalHooks;

      return {
        response: ctx.response,
        toolCalls,
        totalTokens: ctx.totalTokens,
      };
    },
  };

  const runner = new EvalRunner(adapter);

  // Run suite
  const opts: { tags?: string[]; category?: string } = {};
  if (suiteFilter.length > 0) {
    // Try to match as categories first
    const validCategories = ["safety", "personality", "tool_use", "memory", "general"];
    const cats = suiteFilter.filter(s => validCategories.includes(s));
    const tags = suiteFilter.filter(s => !validCategories.includes(s));
    if (cats.length > 0) opts.category = cats[0];
    if (tags.length > 0) opts.tags = tags;
  }

  const result = await runner.runSuite(dataset, opts);

  // Report
  new ConsoleReporter().report(result);

  if (reportFormat === "json" || reportFormat === "all") {
    new JsonReporter().report(result, `eval_${Date.now()}`);
    console.log("JSON report written to eval/results/");
  }
  if (reportFormat === "md" || reportFormat === "all") {
    new MarkdownReporter().report(result, `report_${Date.now()}`);
    console.log("Markdown report written to eval/results/");
  }

  // Store checksum for change detection
  const trigger = new ConfigChangeTrigger(CONFIG_DIR);
  trigger.storeChecksum();

  await agent.shutdown();
  process.exit(result.failed > 0 ? 1 : 0);
}

main().catch(err => { console.error("Eval fatal:", err); process.exit(2); });
