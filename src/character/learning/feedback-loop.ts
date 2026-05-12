/** Feedback Loop — DBNT-style 3-level feedback + FSRS-6 decay.  */
export enum FeedbackLevel { GENTLE = "gentle", NORMAL = "normal", CRITICAL = "critical" }

export interface FeedbackEvent {
  timestamp: number; level: FeedbackLevel; source: string;
  context: string; description: string; pattern: string; applied: boolean;
}

export class FeedbackRule {
  ruleId = ""; content = ""; pattern = ""; level: FeedbackLevel = FeedbackLevel.NORMAL;
  createdAt = 0; lastApplied = 0; applyCount = 0; successCount = 0;
  stability = 0; difficulty = 0.3;
  get isPermanent(): boolean { return this.applyCount >= 3 && this.successRate > 0.66; }
  get successRate(): number { return this.applyCount === 0 ? 0.5 : this.successCount / this.applyCount; }
}

export class FeedbackLoop {
  private _events: FeedbackEvent[] = [];
  private _rules: Map<string, FeedbackRule> = new Map();
  private _rc = 0;
  private _pb: Map<string, number> = new Map();

  recordExplicit(level: FeedbackLevel, ctx: string, desc: string): void {
    this._events.push({ timestamp: Date.now() / 1000, level, source: "explicit", context: ctx, description: desc, pattern: "", applied: false });
    this._check(this._events[this._events.length - 1]);
  }

  inferFromResponse(reply: string, ctx: string): FeedbackEvent | null {
    const rl = reply.toLowerCase(); let e: FeedbackEvent | null = null;
    if (["谢谢", "好的", "明白了", "懂了", "有用", "对", "没错"].some(w => rl.includes(w)))
      e = { timestamp: Date.now() / 1000, level: FeedbackLevel.GENTLE, source: "implicit", context: ctx, description: "正面回应", pattern: "", applied: true };
    else if (["不是", "不对", "理解错了", "再试", "重来"].some(w => rl.includes(w)))
      e = { timestamp: Date.now() / 1000, level: FeedbackLevel.NORMAL, source: "implicit", context: ctx, description: "用户纠正", pattern: "", applied: false };
    if (e) { this._events.push(e); this._check(e); }
    return e;
  }

  recordAutoQuality(qs: number, ctx: string): void {
    if (qs >= 0.7) this.recordExplicit(FeedbackLevel.GENTLE, ctx, `质量${qs.toFixed(2)}`);
    else if (qs < 0.3) this.recordExplicit(FeedbackLevel.NORMAL, ctx, `低质量${qs.toFixed(2)}`);
  }

  private _check(e: FeedbackEvent): void {
    if (e.level === FeedbackLevel.GENTLE) return;
    const p = e.context.slice(0, 80).toLowerCase();
    this._pb.set(p, (this._pb.get(p) ?? 0) + 1);
    if ((this._pb.get(p) ?? 0) >= 3) this._promote(p, e);
  }

  private _promote(p: string, e: FeedbackEvent): void {
    this._rc++; const r = new FeedbackRule();
    r.ruleId = `rule_${this._rc}`; r.content = `避免: ${e.description}`;
    r.pattern = p; r.level = e.level; r.createdAt = Date.now() / 1000;
    this._rules.set(r.ruleId, r); this._pb.set(p, 0);
  }

  getActiveRules(ctx: string): FeedbackRule[] {
    const cl = ctx.toLowerCase(); const rel: FeedbackRule[] = [];
    for (const r of this._rules.values()) {
      if (r.pattern.split(/\s+/).some(w => cl.includes(w))) {
        if (r.lastApplied > 0) {
          const ds = (Date.now() / 1000 - r.lastApplied) / 86400;
          r.stability *= Math.max(0.1, 1 - ds * 0.1);
        }
        r.lastApplied = Date.now() / 1000; r.applyCount++;
        r.stability = Math.min(1, r.stability + 0.1);
        rel.push(r);
      }
    }
    return rel.filter(r => r.isPermanent || r.stability > 0.3);
  }

  recordRuleOutcome(rid: string, success: boolean): void {
    const r = this._rules.get(rid); if (!r) return;
    if (success) { r.successCount++; r.stability = Math.min(1, r.stability + 0.15); }
    else r.stability = Math.max(0, r.stability - 0.1);
  }

  formatRulesForPrompt(rules: FeedbackRule[]): string {
    if (!rules.length) return "";
    return "【经验】\n" + rules.map(r =>
      (r.isPermanent ? "[永久]" : `[学习:${r.stability.toFixed(1)}]`) + " " + r.content
    ).join("\n");
  }

  stats() {
    const all = [...this._rules.values()];
    return { totalEvents: this._events.length, totalRules: all.length, permanent: all.filter(r => r.isPermanent).length };
  }
}
