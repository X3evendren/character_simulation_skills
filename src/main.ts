/**
 * Character Mind v3 — Main Entry
 * readline + ANSI terminal. Works on Windows (PowerShell/cmd) + Unix.
 */
import { CharacterAgent } from "./character/index";
import { OpenAICompatProvider } from "./character/integration/provider";
import { registerBuiltinCommands, router, isCommandInput } from "./commands/index";
import type { CommandContext } from "./commands/types";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { createInterface } from "readline";
import { execSync } from "child_process";
import { StreamRenderer } from "./stream-renderer";
import { HistoryStore } from "./history";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_DIR = resolve(__dirname, "../config");

const API_KEY = process.env.DEEPSEEK_API_KEY || "";
const API_BASE = process.env.DEEPSEEK_API_BASE || "https://api.deepseek.com";
const GEN_MODEL = process.env.GEN_MODEL || "deepseek-v4-pro";
const PSYCH_MODEL = process.env.PSYCH_MODEL || "deepseek-v4-flash";

// ANSI color codes
const CSI = "\x1b[";
const C = {
  reset: `${CSI}0m`, cyan: `${CSI}36m`, green: `${CSI}32m`, yellow: `${CSI}33m`,
  dim: `${CSI}2m`, bold: `${CSI}1m`, white: `${CSI}37m`,
};

function banner() {
  const l = "─".repeat(17);
  console.log(`${C.cyan}┌${l}┐${C.reset}`);
  console.log(`${C.cyan}│${C.reset}   ${C.bold}Character Mind v3${C.reset}     ${C.cyan}│${C.reset}`);
  console.log(`${C.cyan}└${l}┘${C.reset}\n`);
}

async function main() {
  banner();

  if (!API_KEY) {
    console.log("  Set DEEPSEEK_API_KEY environment variable.\n");
    process.exit(1);
  }

  process.stdout.write("Initializing... ");
  const gen = new OpenAICompatProvider(GEN_MODEL, API_KEY, API_BASE);
  const psych = new OpenAICompatProvider(PSYCH_MODEL, API_KEY, API_BASE);
  const agent = new CharacterAgent({
    configDir: CONFIG_DIR, genProvider: gen, psychProvider: psych,
    genModel: GEN_MODEL, psychModel: PSYCH_MODEL,
  });
  await agent.initialize();
  registerBuiltinCommands();
  console.log(`${C.green}ready${C.reset}`);
  console.log(`\n  ${C.bold}${C.cyan}${agent.config.name}${C.reset}${C.bold} · ${C.reset}s=${agent.saturation.s.toFixed(2)}  [/help /quit /stats]\n`);

  const cmdCtx: CommandContext = { agent, args: "", raw: "" };
  const renderer = new StreamRenderer(agent.config.name);
  const history = new HistoryStore();

  process.on("SIGINT", async () => {
    console.log(`\n\n${C.dim}Shutting down...${C.reset}`);
    await agent.shutdown();
    process.exit(0);
  });

  const rl = createInterface({ input: process.stdin, output: process.stdout, terminal: true });
  rl.setPrompt(`${C.white}> ${C.reset}`);
  rl.prompt();

  for await (const line of rl) {
    const input = line.trim();
    if (!input) { rl.prompt(); continue; }

    // ── Bash mode: !command → execute shell ──
    if (input.startsWith("!")) {
      const cmd = input.slice(1).trim();
      try {
        const out = execSync(cmd, { encoding: "utf-8", timeout: 30000 });
        console.log(out);
      } catch (e: any) {
        console.log(`${C.yellow}${e.stderr || e.message}${C.reset}`);
      }
      rl.prompt(); continue;
    }

    // ── Command dispatch ──
    if (isCommandInput(input)) {
      const result = await router.dispatch(input, { ...cmdCtx, raw: input, args: "" });
      if (result.type === "local") {
        if (result.output) console.log(`\n${result.output}\n`);
        if (result.commandName === "quit" || result.commandName === "exit") break;
        rl.prompt(); continue;
      }
      if (result.type === "prompt" && result.promptText) {
        // PromptCommand: send the expanded prompt to the agent
        const start = Date.now();
        process.stdout.write(`${C.yellow}${agent.config.name}: ${C.reset}`);
        const ctx = await agent.run(result.promptText, async (delta: string) => {
          process.stdout.write(delta);
        });
        const elapsed = ((Date.now() - start) / 1000).toFixed(1);
        console.log(`${C.dim}\n  [t${agent.turnCount}  ${elapsed}s]${C.reset}\n`);
        rl.prompt(); continue;
      }
      if (result.type === "unknown" && result.output) {
        console.log(`\n${result.output}\n`);
        rl.prompt(); continue;
      }
    }

    // ── Normal mode: talk to agent ──
    history.add(input);
    renderer.showSpinner("analyzing");

    // Hook: tool calls → display
    agent.hooks = [{
      beforeBuild: async () => { renderer.setPhase("generating"); },
    }];

    const ctx = await agent.run(input, async (delta: string) => {
      renderer.onDelta(delta);
    });

    if (ctx.totalTokens) renderer.setTokens(ctx.totalTokens);
    renderer.onEnd(agent.turnCount);
    rl.prompt();
  }

  console.log("\nShutting down...");
  await agent.shutdown();
  console.log("Goodbye!");
  rl.close();
  process.exit(0);
}

export { main };
