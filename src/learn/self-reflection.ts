/** Self Reflection — Dual-process fast/slow reflection.  */
export interface ReflectionEntry {
  timestamp: number; type: "fast" | "slow";
  whatWentWell: string; whatWentWrong: string; insight: string; actionItems: string[];
}

export class SelfReflection {
  fastInterval: number;
  slowInterval: number;

  private _entries: ReflectionEntry[] = [];
  private _turnBuf: Array<Record<string, string>> = [];
  private _lastSlow = 0;

  constructor(fi = 1, si = 20) { this.fastInterval = fi; this.slowInterval = si; }

  fastReflect(userInput: string, assistantResponse: string, psychologyResult?: any): ReflectionEntry {
    let ww = "", wr = "";
    if (assistantResponse.length < 10) wr = "回应太短";
    else if (assistantResponse.length > 500) wr = "回应太长";
    if (psychologyResult?.emotion?.intensity > 0.8) ww = `情感强度高(${psychologyResult.emotion.dominant})`;

    const e: ReflectionEntry = {
      timestamp: Date.now() / 1000, type: "fast",
      whatWentWell: ww || "正常", whatWentWrong: wr || "无明显问题",
      insight: "", actionItems: [],
    };
    this._entries.push(e);
    this._turnBuf.push({ user: userInput.slice(0, 200), assistant: assistantResponse.slice(0, 200), well: ww, wrong: wr });
    if (this._entries.length > 200) this._entries = this._entries.slice(-200);
    if (this._turnBuf.length > 50) this._turnBuf = this._turnBuf.slice(-50);
    return e;
  }

  shouldSlowReflect(turnCount: number): boolean { return turnCount % this.slowInterval === 0 && turnCount > 0; }
  shouldSessionReflect(): boolean { return this._turnBuf.length > 0; }

  async slowReflect(provider: any, selfModel: any, skillLibrary: any): Promise<string[]> {
    if (!this._turnBuf.length) return [];
    const recent = this._turnBuf.slice(-20);
    const summary = recent.map((t, i) =>
      `${i + 1}. 用户: ${t.user.slice(0, 60)}\n   助手: ${t.assistant.slice(0, 60)}`
    ).join("\n");
    try {
      const resp = await provider.chat(
        [{ role: "user", content: `回顾交互，识别重复失败模式。\n${summary}\n输出要点。` }], 0.3, 400,
      );
      const analysis = (resp.content ?? "").trim();
      const insights = analysis.split("\n")
        .filter((l: string) => l.trim().startsWith("-") || l.trim().startsWith("1."))
        .map((l: string) => l.trim().replace(/^[-\d.]+\s*/, ""));

      this._entries.push({
        timestamp: Date.now() / 1000, type: "slow",
        whatWentWell: "", whatWentWrong: "",
        insight: analysis.slice(0, 500), actionItems: insights.slice(0, 5),
      });
      this._lastSlow = Date.now() / 1000;

      const failures = recent.filter(t => t.wrong && t.wrong !== "无明显问题");
      if (failures.length >= 3 && skillLibrary) {
        await skillLibrary.evolve(
          failures.map(t => t.user.slice(0, 50)).join("; "),
          failures.map(t => t.wrong).join("; "),
          provider,
        );
      }
      if (insights.length && selfModel) {
        selfModel.recordGrowth("reflection", `反思: ${insights[0] ?? ""}`, 0.6);
      }
      return insights;
    } catch { return []; }
  }

  getRecentInsights(n = 5): string[] {
    return this._entries.filter(e => e.type === "slow").slice(-n).map(e => e.insight.slice(0, 200)).filter(Boolean);
  }

  stats() {
    return {
      totalReflections: this._entries.length,
      fastCount: this._entries.filter(e => e.type === "fast").length,
      slowCount: this._entries.filter(e => e.type === "slow").length,
      recentInsights: this.getRecentInsights(3),
    };
  }
}
