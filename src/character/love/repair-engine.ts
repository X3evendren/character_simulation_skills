/** Repair Engine — 4-phase rupture repair. 1:1 from core/love/repair_engine.py */
export enum RepairPhase { IDLE = "idle", PERSPECTIVE_FLIP = "perspective_flip", RESPONSIBILITY_CHECK = "responsibility_check", RE_OATH_DECISION = "re_oath_decision", NARRATIVE_INTEGRATION = "narrative_integration", COMPLETE = "complete", FAILED = "failed" }

export class RepairResult {
  success = false; phaseReached: RepairPhase = RepairPhase.IDLE;
  gapDescription = ""; chosenResponse = ""; reOathDecision = false;
  narrativeUpdate = ""; timestamp = 0;
}

export class RepairEngine {
  currentPhase: RepairPhase = RepairPhase.IDLE;
  private _gap = ""; private _resp = "";

  async run(
    breachEvent: string, selfModel: any, otherModel: Record<string, any>,
    weNarrative: string, oath: any, provider: any,
  ): Promise<RepairResult> {
    this.currentPhase = RepairPhase.IDLE;
    this.currentPhase = RepairPhase.PERSPECTIVE_FLIP;
    const gap = await this._flip(breachEvent, otherModel, provider);
    if (!gap) return Object.assign(new RepairResult(), { success: false, phaseReached: RepairPhase.PERSPECTIVE_FLIP, timestamp: Date.now() / 1000 });
    this._gap = gap;

    this.currentPhase = RepairPhase.RESPONSIBILITY_CHECK;
    const chosen = await this._check(gap, provider);
    if (!chosen) return Object.assign(new RepairResult(), { success: false, phaseReached: RepairPhase.RESPONSIBILITY_CHECK, gapDescription: gap, timestamp: Date.now() / 1000 });
    this._resp = chosen;

    this.currentPhase = RepairPhase.RE_OATH_DECISION;
    const will = this._decide(oath);
    if (!will) {
      if (oath) oath.terminate();
      return Object.assign(new RepairResult(), { success: false, phaseReached: RepairPhase.RE_OATH_DECISION, gapDescription: gap, chosenResponse: chosen, reOathDecision: false, timestamp: Date.now() / 1000 });
    }
    if (oath) oath.repair("修复: " + breachEvent.slice(0, 80));

    this.currentPhase = RepairPhase.NARRATIVE_INTEGRATION;
    const narr = await this._integrate(breachEvent, gap, chosen, weNarrative, selfModel, provider);
    this.currentPhase = RepairPhase.COMPLETE;
    return Object.assign(new RepairResult(), { success: true, phaseReached: RepairPhase.COMPLETE, gapDescription: gap, chosenResponse: chosen, reOathDecision: true, narrativeUpdate: narr, timestamp: Date.now() / 1000 });
  }

  private async _flip(evt: string, om: Record<string, any>, p: any): Promise<string> {
    try {
      const msg = `你在尝试理解另一个人的感受。\n事件: ${evt}\n\n你对这个人的了解:\n${JSON.stringify(om)}\n\n请用第一人称描述他的感受。不要分析。`;
      const r = await p.chat([{ role: "user", content: msg }], 0.3, 300);
      return (r.content ?? "").trim().slice(0, 500);
    } catch { return ""; }
  }

  private async _check(gap: string, p: any): Promise<string> {
    try {
      const msg = `你发现你可能伤害了在乎的人。\n对方的感受:\n${gap}\n\n承认伤害，不找借口。表达愿意被改变。不要求原谅。写一句话回应。`;
      const r = await p.chat([{ role: "user", content: msg }], 0.5, 150);
      return (r.content ?? "").trim().slice(0, 200);
    } catch { return ""; }
  }

  private _decide(oath: any): boolean {
    if (!oath) return false;
    const rc = (oath.history ?? []).filter((e: any) => e.eventType === "repaired").length;
    return rc < 3;
  }

  private async _integrate(evt: string, gap: string, resp: string, wn: string, sm: any, p: any): Promise<string> {
    try {
      const msg = `将裂痕织入叙事。\n裂痕: ${evt}\n伤害: ${gap}\n回应: ${resp}\n之前叙事: ${wn}\n\n写1-2句话。温暖不煽情。`;
      const r = await p.chat([{ role: "user", content: msg }], 0.5, 200);
      const n = (r.content ?? "").trim().slice(0, 300);
      if (sm && typeof sm.recordGrowth === "function") sm.recordGrowth("relationship_repair", "经历裂痕修复: " + n, 0.85);
      return n;
    } catch { return ""; }
  }
}
