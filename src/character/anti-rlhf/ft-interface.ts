export interface FTSample { original: string; rewritten: string; context: string; patternDetected: string; timestamp: number }

export class FTInterface {
  minSamples: number; private s: FTSample[] = []; private ec = 0;
  constructor(ms = 50) { this.minSamples = ms; }

  collect(o: string, rw: string, ctx: string, pat = ""): void {
    this.s.push({ original: o, rewritten: rw, context: ctx, patternDetected: pat, timestamp: Date.now() / 1000 });
    if (this.s.length > 1000) this.s = this.s.slice(-1000);
  }

  get shouldPromptFT(): boolean { return (this.s.length - this.ec) >= this.minSamples; }

  getPromptMessage(): string {
    const n = this.s.length - this.ec;
    return `已收集 ${n} 条角色一致性微调样本。总计 ${this.s.length} 条。`;
  }

  exportOpenAIJSONL(): string {
    const l: string[] = [];
    for (const x of this.s) {
      l.push(JSON.stringify({
        messages: [
          { role: "system", content: "你是一个角色一致的助手。" },
          { role: "user", content: x.original },
          { role: "assistant", content: x.rewritten },
        ],
      }));
    }
    this.ec = this.s.length;
    return l.join("\n");
  }

  get sampleCount(): number { return this.s.length; }
}
