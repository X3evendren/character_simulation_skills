export enum ChangeSpeed { RAPID = "rapid", MEDIUM = "medium", SLOW = "slow" }

export class Param {
  name: string; rangeMin: number; rangeMax: number;
  defaultVal: number; speed: ChangeSpeed; description: string;
  baseline: number; activation: number;

  constructor(name: string, rangeMin = 0, rangeMax = 1, defaultVal = 0.5, speed = ChangeSpeed.MEDIUM, desc = "") {
    this.name = name; this.rangeMin = rangeMin; this.rangeMax = rangeMax;
    this.defaultVal = defaultVal; this.speed = speed; this.description = desc;
    this.baseline = defaultVal; this.activation = 0;
  }
  get effective(): number {
    const v = this.baseline + this.activation * (1 - this.baseline);
    return Math.max(this.rangeMin, Math.min(this.rangeMax, v));
  }
  setActivation(v: number) { this.activation = Math.max(0, Math.min(1, v)); }
  setBaseline(v: number) { this.baseline = Math.max(this.rangeMin, Math.min(this.rangeMax, v)); }
  decayActivation(r = 0.3) { this.activation *= (1 - r); }
  toDict() { return { baseline: +this.baseline.toFixed(3), activation: +this.activation.toFixed(3), effective: +this.effective.toFixed(3), speed: this.speed }; }
}

export class UnifiedParams {
  pleasure = new Param("pleasure", -1, 1, 0, ChangeSpeed.RAPID, "PAD愉悦度");
  arousal = new Param("arousal", 0, 1, 0.3, ChangeSpeed.RAPID, "PAD唤醒度");
  dominance = new Param("dominance", -1, 1, 0, ChangeSpeed.MEDIUM, "PAD支配感");
  joy = new Param("joy", 0, 1, 0.3, ChangeSpeed.RAPID, "喜悦");
  sadness = new Param("sadness", 0, 1, 0.15, ChangeSpeed.RAPID, "悲伤");
  trust = new Param("trust", 0, 1, 0.4, ChangeSpeed.MEDIUM, "信任");
  disgust = new Param("disgust", 0, 1, 0.05, ChangeSpeed.RAPID, "厌恶");
  fear = new Param("fear", 0, 1, 0.15, ChangeSpeed.RAPID, "恐惧");
  anger = new Param("anger", 0, 1, 0.05, ChangeSpeed.RAPID, "愤怒");
  surprise = new Param("surprise", 0, 1, 0.1, ChangeSpeed.RAPID, "惊讶");
  anticipation = new Param("anticipation", 0, 1, 0.2, ChangeSpeed.MEDIUM, "期待");
  goalConduciveness = new Param("goalConduciveness", -1, 1, 0, ChangeSpeed.RAPID, "目标促进");
  goalRelevance = new Param("goalRelevance", 0, 1, 0.5, ChangeSpeed.RAPID, "目标相关性");
  copingPotential = new Param("copingPotential", 0, 1, 0.5, ChangeSpeed.MEDIUM, "应对潜力");
  unexpectedness = new Param("unexpectedness", 0, 1, 0.5, ChangeSpeed.RAPID, "意外程度");
  certainty = new Param("certainty", 0, 1, 0.5, ChangeSpeed.MEDIUM, "确定性");
  urgency = new Param("urgency", 0, 1, 0.3, ChangeSpeed.RAPID, "紧迫性");
  futureExpectancy = new Param("futureExpectancy", 0, 1, 0.5, ChangeSpeed.SLOW, "未来预期");
  normCompatibility = new Param("normCompatibility", -1, 1, 0, ChangeSpeed.SLOW, "规范相容性");
  legitimacy = new Param("legitimacy", -1, 1, 0, ChangeSpeed.MEDIUM, "正当性");
  intimacy = new Param("intimacy", 0, 1, 0.2, ChangeSpeed.SLOW, "亲密感");
  passion = new Param("passion", 0, 1, 0.2, ChangeSpeed.MEDIUM, "激情");
  commitment = new Param("commitment", 0, 1, 0.3, ChangeSpeed.SLOW, "承诺");
  sexualBaseline = new Param("sexualBaseline", 0, 1, 0.05, ChangeSpeed.SLOW, "性舒适度基线");
  sexualActivation = new Param("sexualActivation", 0, 1, 0, ChangeSpeed.RAPID, "性唤起快分量");
  positiveRatio = new Param("positiveRatio", 0, 10, 3, ChangeSpeed.MEDIUM, "正负互动比");
  floodingRisk = new Param("floodingRisk", 0, 1, 0.2, ChangeSpeed.RAPID, "情绪淹没");
  repairDetected = new Param("repairDetected", 0, 1, 0, ChangeSpeed.RAPID, "修复检测");
  defenseIntensity = new Param("defenseIntensity", 0, 1, 0.15, ChangeSpeed.RAPID, "防御强度");
  defenseLevel = new Param("defenseLevel", 1, 4, 3, ChangeSpeed.SLOW, "防御成熟度");
  threatPrecision = new Param("threatPrecision", 0, 1, 0.3, ChangeSpeed.RAPID, "威胁精度");
  safetyPrecision = new Param("safetyPrecision", 0, 1, 0.5, ChangeSpeed.RAPID, "安全精度");
  autonomy = new Param("autonomy", 0, 1, 0.5, ChangeSpeed.SLOW, "自主性");
  competence = new Param("competence", 0, 1, 0.5, ChangeSpeed.MEDIUM, "胜任感");
  relatedness = new Param("relatedness", 0, 1, 0.4, ChangeSpeed.MEDIUM, "归属感");
  intrinsicMotivation = new Param("intrinsicMotivation", 0, 1, 0.5, ChangeSpeed.MEDIUM, "内在动机");
  dominantNeed = new Param("dominantNeed", 1, 5, 3, ChangeSpeed.SLOW, "主导需求");
  attachmentActivation = new Param("attachmentActivation", 0, 1, 0.3, ChangeSpeed.RAPID, "依恋激活");
  selfWorth = new Param("selfWorth", 0, 1, 0.6, ChangeSpeed.SLOW, "自我价值");
  expressiveness = new Param("expressiveness", 0, 1, 0.3, ChangeSpeed.SLOW, "表达开放度");
  playfulness = new Param("playfulness", 0, 1, 0.15, ChangeSpeed.MEDIUM, "玩心");
  schemaReinforcement = new Param("schemaReinforcement", 0, 1, 0.5, ChangeSpeed.SLOW, "图式强化");
  aceActivation = new Param("aceActivation", 0, 1, 0, ChangeSpeed.RAPID, "ACE创伤");
  selfUpdateOpenness = new Param("selfUpdateOpenness", 0, 1, 0.15, ChangeSpeed.SLOW, "被重塑开放度");
  oathStrength = new Param("oathStrength", 0, 1, 0, ChangeSpeed.SLOW, "誓约强度");
  irreducibilityGamma = new Param("irreducibilityGamma", 0, 1, 0, ChangeSpeed.SLOW, "不可压缩性先验");

  allParams(): Record<string, Param> {
    const r: Record<string, Param> = {};
    for (const [k, v] of Object.entries(this)) { if (v instanceof Param) r[k] = v; }
    return r;
  }
  get(name: string): Param | undefined { return this.allParams()[name]; }
  bySpeed(s: ChangeSpeed): Record<string, Param> { const r: Record<string, Param> = {}; for (const [n,p] of Object.entries(this.allParams())) { if (p.speed===s) r[n]=p; } return r; }
  decayAllActivations(rate=0.25) { for (const p of Object.values(this.allParams())) { if (p.speed===ChangeSpeed.RAPID) p.decayActivation(rate); else if (p.speed===ChangeSpeed.MEDIUM) p.decayActivation(rate*0.3); } }
  trueEffective(name: string): number { const p=this.get(name); if(!p)return 0; if(name==="sexualActivation"){const sb=this.sexualBaseline.effective;return sb+p.activation*(1-sb)}if(name==="playfulness")return p.effective*(0.3+0.7*this.safetyPrecision.effective);if(name==="expressiveness")return p.effective*(0.2+0.8*this.intimacy.baseline);if(name==="intimacy")return p.effective*(0.5+0.5*this.selfWorth.effective);return p.effective; }
  checkCoherence(): string[] { const v:string[]=[]; if(this.threatPrecision.effective>0.7&&this.safetyPrecision.effective>0.7)v.push("威胁精度和安全精度同时>0.7"); if(this.playfulness.effective>0.6&&this.sadness.effective>0.6)v.push("玩心和悲伤同时>0.6"); if(this.defenseIntensity.effective>0.6&&this.selfUpdateOpenness.effective>0.5)v.push("高防御+高自我更新开放"); if(this.fear.effective>0.8&&this.anger.effective>0.8)v.push("恐惧和愤怒同时>0.8"); return v; }
  autoCorrect() { const vs=this.checkCoherence(); if(!vs.length)return; for(const vv of vs){if(vv.includes("威胁")){if(this.threatPrecision.effective>this.safetyPrecision.effective)this.safetyPrecision.activation*=0.3;else this.threatPrecision.activation*=0.3}if(vv.includes("玩心")){this.playfulness.activation*=0.3;this.sadness.activation*=0.3}if(vv.includes("高防御"))this.selfUpdateOpenness.activation*=0.3;if(vv.includes("恐惧")){this.fear.activation*=0.5;this.anger.activation*=0.5}} }
  snapshot(): Record<string,number> { const s:Record<string,number>={}; for(const[n,p]of Object.entries(this.allParams()))s[n]=+p.effective.toFixed(3); return s; }
  applySnapshot(snap: Record<string,number>) { for(const[n,v]of Object.entries(snap))this.get(n)?.setActivation(v); }
}