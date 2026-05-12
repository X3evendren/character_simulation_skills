/**
 * StreamRenderer — Clean terminal display.
 * No cursor tricks, no spinner animation (unreliable in pipes).
 * Just clean text output with ANSI colors.
 */
const CSI = "\x1b[";
const C = {
  reset: `${CSI}0m`, yellow: `${CSI}33m`, green: `${CSI}32m`, red: `${CSI}31m`,
  dim: `${CSI}2m`, bold: `${CSI}1m`, cyan: `${CSI}36m`,
};

export type AgentPhase = "idle" | "analyzing" | "generating" | "done";

export class StreamRenderer {
  private buf = "";
  private phase: AgentPhase = "idle";
  private startTime = 0;
  private botName: string;
  private totalTokens = 0;
  private started = false;

  constructor(botName = "assistant") { this.botName = botName; }

  showSpinner(_phase?: AgentPhase): void {
    this.startTime = Date.now();
    this.phase = "analyzing";
    this.started = false;
    // Simple: just print a line indicating thinking
    process.stdout.write(`${C.dim}  ${this.botName} thinking...${C.reset}\n`);
  }

  setPhase(phase: AgentPhase): void { this.phase = phase; }

  showTool(tool: string, detail: string): void {
    const icons: Record<string, string> = { read_file: "📄", exec_command: "$", search_files: "🔍" };
    const icon = icons[tool] ?? "↳";
    process.stdout.write(`  ${C.dim}${icon} ${tool} ${detail}${C.reset}\n`);
  }

  showToolResult(success: boolean, summary: string): void {
    const mark = success ? `${C.green}✓${C.reset}` : `${C.red}✗${C.reset}`;
    process.stdout.write(`  ${mark} ${C.dim}${summary}${C.reset}\n`);
  }

  onDelta(delta: string): void {
    if (!this.started) {
      this.started = true;
      // Kill the "thinking..." line visually by printing over it
      process.stdout.write(`\r${C.yellow}${C.bold}${this.botName}:${C.reset} `);
      this.phase = "generating";
    }
    this.buf += delta;
    process.stdout.write(delta);
  }

  setTokens(t: number): void { this.totalTokens = t; }

  onEnd(turnCount: number): void {
    const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(1);
    const tokStr = this.totalTokens > 0 ? ` · ${this.totalTokens}t` : "";
    console.log(`${C.dim}\n  [t${turnCount} · ${elapsed}s${tokStr}]${C.reset}\n`);
    this.reset();
  }

  reset(): void {
    this.buf = "";
    this.phase = "idle";
    this.totalTokens = 0;
    this.started = false;
  }
}
