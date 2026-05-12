import { UnifiedParams, ChangeSpeed } from "./unified-params";

export interface ModulationRecord {
  source: string;
  shifts: Record<string, number>;
  reason: string;
  coherenceViolations: string[];
}

/** Fast Track: only emotional tone parameters (Hot Path) */
const ALLOWED_FAST = new Set([
  "pleasure", "arousal", "dominance",
  "joy", "sadness", "fear", "anger", "surprise", "trust", "anticipation",
]);

/** Slow Track: only relationship + self parameters (Cold Path, baseline only) */
const ALLOWED_SLOW = new Set([
  "intimacy", "trust", "commitment", "expressiveness",
  "attachmentActivation", "selfWorth", "selfUpdateOpenness", "relatedness",
]);

export class ParamsModulator {
  params: UnifiedParams;
  history: ModulationRecord[] = [];

  constructor(params: UnifiedParams) { this.params = params; }

  modulateFast(psych: any): Record<string, number> {
    const shifts: Record<string, number> = {};
    const emo = psych.emotion;
    const att = psych.attachment;
    const df = psych.defense;
    const app = psych.appraisal;

    if (emo.dominant !== "neutral") {
      const dom = emo.dominant;
      if (["joy","sadness","fear","anger","disgust","surprise","trust","anticipation"].includes(dom)) {
        shifts[dom] = emo.intensity;
      }
      shifts["pleasure"] = emo.pleasure;
      shifts["arousal"] = emo.arousal;
      shifts["dominance"] = emo.dominance;
    }

    shifts["goalConduciveness"] = app.goalConduciveness;
    shifts["copingPotential"] = app.copingPotential;
    shifts["unexpectedness"] = 1 - app.copingPotential;

    if (df.intensity > 0.1) {
      shifts["defenseIntensity"] = df.intensity;
      if (df.active && df.active.includes("投射")) shifts["threatPrecision"] = 0.6;
      else if (df.active && df.active.includes("退行")) shifts["attachmentActivation"] = 0.7;
    }

    if (att.activation > 0.3) {
      shifts["attachmentActivation"] = att.activation;
      if (att.strategy === "seeking_reassurance") {
        shifts["safetyPrecision"] = -0.3;
        shifts["relatedness"] = 0.7;
      } else if (att.strategy === "distancing") {
        shifts["safetyPrecision"] = 0.2;
        shifts["defenseIntensity"] = Math.max(shifts["defenseIntensity"] ?? 0, 0.4);
      }
    }

    const inner = psych.innerMonologue || "";
    if (inner) {
      const touchWords = ["触动","打动","感动","温暖","被看到","被理解","他在乎","他记得","原来他"];
      if (touchWords.some(w => inner.includes(w))) { shifts["selfUpdateOpenness"] = 0.3; shifts["intimacy"] = 0.15; }
      const threatWords = ["危险","不安","不确定","害怕","失去","离开","抛弃"];
      if (threatWords.some(w => inner.includes(w))) { shifts["threatPrecision"] = Math.max(shifts["threatPrecision"]??0, 0.6); shifts["safetyPrecision"] = -0.5; }
      const sexualWords = ["想要","渴望","靠近","触碰","好看","吸引","心跳","身体"];
      if (sexualWords.some(w => inner.includes(w))) { shifts["sexualActivation"] = 0.6; shifts["passion"] = 0.4; }
      const playWords = ["逗","闹","撒娇","黏","调皮","玩笑"];
      if (playWords.some(w => inner.includes(w))) shifts["playfulness"] = 0.5;
      const jealousyWords = ["别人","她是谁","为什么对她","只对我","我的","属于我","不许","吃醋","在意"];
      if (jealousyWords.some(w => inner.includes(w))) {
        shifts["fear"] = (shifts["fear"]??0) + 0.3;
        shifts["attachmentActivation"] = 0.6;
        shifts["relatedness"] = 0.8;
        shifts["playfulness"] = -0.3;
      }
    }

    const filtered: Record<string, number> = {};
    for (const [k,v] of Object.entries(shifts)) { if (ALLOWED_FAST.has(k) && Math.abs(v) > 0.02) filtered[k] = v; }
    this.history.push({ source: "fast", shifts: filtered, reason: "emotion=" + emo.dominant + ", intensity=" + emo.intensity.toFixed(1), coherenceViolations: [] });
    return filtered;
  }

  modulateSlow(psych: any, memoryCtx = "", fastShifts?: Record<string,number>|null, selfNarrative = ""): Record<string,number> {
    const shifts: Record<string,number> = {};
    if (fastShifts) {
      const emo = psych.emotion;
      if ((fastShifts["anger"]??0) > 0.5 && emo.dominant === "sadness") {
        shifts["anger"] = -(fastShifts["anger"]??0) * 0.8;
        shifts["sadness"] = emo.intensity * 1.2;
        shifts["playfulness"] = -0.3;
      }
      if ((fastShifts["threatPrecision"]??0) > 0.5 && emo.dominant === "joy") {
        shifts["threatPrecision"] = -0.5;
        shifts["safetyPrecision"] = 0.5;
      }
      if ((fastShifts["sexualActivation"]??0) > 0.4 && psych.defense?.intensity > 0.5) {
        shifts["sexualActivation"] = -0.3;
      }
    }

    const slowDeltas = this._computeBaselineDeltas(psych, memoryCtx, selfNarrative);
    for (const [k,v] of Object.entries(slowDeltas)) shifts[k] = v;

    const filtered: Record<string,number> = {};
    for (const [k,v] of Object.entries(shifts)) { if (ALLOWED_SLOW.has(k) && Math.abs(v) > 0.005) filtered[k] = v; }
    this.history.push({ source: "slow", shifts: filtered, reason: "baseline_deltas=" + Object.keys(slowDeltas).length, coherenceViolations: [] });
    return filtered;
  }

  private _computeBaselineDeltas(psych: any, memCtx: string, selfN: string): Record<string,number> {
    const deltas: Record<string,number> = {};
    const emo = psych.emotion;
    if (emo.pleasure > 0.3 && emo.intensity > 0.4) deltas["intimacy"] = 0.01;
    if (emo.dominant === "trust" && emo.intensity > 0.6) deltas["intimacy"] = (deltas["intimacy"]??0) + 0.02;
    if (emo.dominant === "trust" && (psych.attachment?.activation??0) > 0.5) deltas["commitment"] = 0.01;
    if (emo.pleasure > 0.5 && (psych.appraisal?.copingPotential??0) > 0.6) deltas["selfWorth"] = 0.01;
    if (emo.pleasure > 0.4 && emo.intensity > 0.3) deltas["expressiveness"] = 0.005;
    if (["joy","trust","love"].includes(emo.dominant) && emo.intensity > 0.5 && emo.pleasure > 0.3) deltas["sexualBaseline"] = 0.01;
    const inner = psych.innerMonologue || "";
    if (inner && ["触动","改变","原来","他教会","因为他"].some(w => inner.includes(w))) deltas["selfUpdateOpenness"] = 0.02;

    const profound = ["我爱你","永远","承诺","嫁","娶","一生","最重要","没有你我","你是我的","我们需要谈谈"];
    const isProfound = memCtx && profound.some(w => memCtx.includes(w));
    const cap = isProfound ? 0.10 : 0.03;
    const r: Record<string,number> = {};
    for (const [k,v] of Object.entries(deltas)) r[k] = Math.max(-cap, Math.min(cap, v * (isProfound ? 3 : 1)));
    return r;
  }

  applyShifts(shifts: Record<string,number>, isBaseline = false): void {
    for (const [name, delta] of Object.entries(shifts)) {
      const p = this.params.get(name);
      if (!p) continue;
      if (isBaseline || p.speed === ChangeSpeed.SLOW) {
        p.setBaseline(p.baseline + delta);
      } else {
        if (delta >= 0) p.setActivation(delta);
        else p.setActivation(Math.max(0, p.activation + delta));
      }
    }
    const violations = this.params.checkCoherence();
    if (violations.length) {
      this.params.autoCorrect();
      if (this.history.length) this.history[this.history.length-1].coherenceViolations = violations;
    }
  }

  stats(): Record<string,number> {
    return {
      totalModulations: this.history.length,
      fastCount: this.history.filter(r => r.source === "fast").length,
      slowCount: this.history.filter(r => r.source === "slow").length,
      corrections: this.history.filter(r => r.source === "slow" && Object.values(r.shifts).some(v => v < 0)).length,
      coherenceViolations: this.history.reduce((s,r) => s + r.coherenceViolations.length, 0),
    };
  }
}