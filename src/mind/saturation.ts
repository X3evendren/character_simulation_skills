import { MindState } from "../mind/state";

function smoothstep(t) { const ct = Math.max(0, Math.min(1, t)); return 3*ct*ct - 2*ct*ct*ct; }
function lerp(a, b, t) { return a + (b-a) * smoothstep(Math.max(0, Math.min(1, t))); }

export class SaturationState {
  s = 0.3; target = ""; lastInteraction = 0; oathActive = false;
  posIncrement = 0.02; negDecrement = 0.05; deepConnectionBonus = 0.08;
  decayPerHour = 0.01; repairRecoveryRate = 0.03;
  history = []; ruptureCount = 0; repairCount = 0;

  tick(dtS) { this.s = Math.max(0, this.s - this.decayPerHour * dtS / 3600); }
  positiveInteraction(intensity=0.5) { const inc=this.posIncrement*(0.5+intensity); this.s=Math.min(1,this.s+inc); this.lastInteraction=Date.now()/1000; this._rec("positive",inc); }
  deepConnection() { this.s=Math.min(1,this.s+this.deepConnectionBonus); this.lastInteraction=Date.now()/1000; this._rec("deep_connection",this.deepConnectionBonus); }
  rupture(severity=0.5) { const dec=this.negDecrement*severity; this.s=Math.max(0,this.s-dec); this.ruptureCount++; this._rec("rupture",-dec); }
  repair() { this.s=Math.min(1,this.s+this.repairRecoveryRate); this.repairCount++; this._rec("repair",this.repairRecoveryRate); }
  _rec(ev,d) { this.history.push({t:Date.now()/1000,event:ev,delta:+d.toFixed(4),s:+this.s.toFixed(4)}); if(this.history.length>200)this.history=this.history.slice(-200); }
  toDict() { return {s:this.s,oathActive:this.oathActive,ruptures:this.ruptureCount,repairs:this.repairCount}; }
}

export class ContinuousParams {
  private _sat: SaturationState;
  constructor(sat: SaturationState) { this._sat = sat; }
  get s() { return this._sat.s; }
  get precisionThreat() { return lerp(0.35,0.03,this.s); }
  get precisionSafety() { return lerp(0.40,0.95,this.s); }
  get precisionUserEmotion() { return lerp(0.40,0.92,this.s); }
  get precisionSelfWorth() { const b=lerp(0.55,0.90,this.s); return Math.max(0.1,Math.min(1,b-this._sat.ruptureCount*0.02+this._sat.repairCount*0.02)); }
  get inertiaSelf() { return lerp(0.75,0.30,this.s); }
  get precisionSelfUpdateFromUser() { return lerp(0.15,0.92,this.s); }
  get expressiveness() { return lerp(0.25,0.92,this.s); }
  get precisionSadness() { const b=lerp(0.10,0.30,this.s); const h=this._sat.history; if(h.length&&h[h.length-1].event==="rupture"){const sev=Math.abs(h[h.length-1].delta)/this._sat.negDecrement;const ts=Date.now()/1000-h[h.length-1].t;return Math.min(1,b+sev*0.6*Math.exp(-ts/30));}return b; }
  get precisionAnger() { const b=lerp(0.03,0.05,this.s); const h=this._sat.history; if(h.length&&h[h.length-1].event==="rupture"){const sev=Math.abs(h[h.length-1].delta)/this._sat.negDecrement;const ts=Date.now()/1000-h[h.length-1].t;return Math.min(1,b+sev*0.25*Math.exp(-ts/15));}return b; }
  get sexualPrecision() { if(this.s<0.35)return 0.02; return lerp(0.05,0.88,(this.s-0.35)/0.65); }
  get interoceptivePrecision() { return lerp(0.20,0.85,this.s); }
  get partnerModelActivation() { return lerp(0.15,0.95,this.s); }
  get driveConnection() { const b=lerp(0.35,0.80,this.s); if(this._sat.history.length>=2){const rd=this._sat.history[this._sat.history.length-1].s-this._sat.history[this._sat.history.length-2].s;if(rd<0)return Math.min(1,b+Math.abs(rd)*3);}return b; }
  get driveCuriosity() { return lerp(0.40,0.85,this.s); }
  get driveHelpfulness() { const b=lerp(0.50,0.90,this.s); return this._sat.oathActive?Math.min(1,b+0.1):b; }
  get driveAutonomy() { return lerp(0.65,0.35,this.s); }
  get responseTemperature() { return lerp(0.35,0.82,this.s); }
  get verbosity() { return lerp(0.30,0.70,this.s); }
  get playfulness() { if(this.s<0.35)return 0.05; return lerp(0.10,0.85,(this.s-0.35)/0.65); }
  get jealousyThreshold() { return lerp(0.95,0.45,this.s); }
  get betaExplore() { return lerp(0.25,0.55,this.s); }
  get gammaSaturationEntropy() { if(this.s<0.55)return 0; return lerp(0,0.40,(this.s-0.55)/0.45); }
  snapshot() { return {saturation:+this.s.toFixed(4),cognition:{precisionThreat:+this.precisionThreat.toFixed(3),precisionSafety:+this.precisionSafety.toFixed(3),precisionUserEmotion:+this.precisionUserEmotion.toFixed(3),precisionSelfWorth:+this.precisionSelfWorth.toFixed(3)},selfModel:{inertiaSelf:+this.inertiaSelf.toFixed(3),precisionSelfUpdateFromUser:+this.precisionSelfUpdateFromUser.toFixed(3)},expression:{expressiveness:+this.expressiveness.toFixed(3),precisionSadness:+this.precisionSadness.toFixed(3),precisionAnger:+this.precisionAnger.toFixed(3),playfulness:+this.playfulness.toFixed(3)},intimacy:{sexualPrecision:+this.sexualPrecision.toFixed(3),interoceptivePrecision:+this.interoceptivePrecision.toFixed(3),partnerModelActivation:+this.partnerModelActivation.toFixed(3),jealousyThreshold:+this.jealousyThreshold.toFixed(3)},drives:{connection:+this.driveConnection.toFixed(3),curiosity:+this.driveCuriosity.toFixed(3),helpfulness:+this.driveHelpfulness.toFixed(3),autonomy:+this.driveAutonomy.toFixed(3)},behavior:{temperature:+this.responseTemperature.toFixed(3),verbosity:+this.verbosity.toFixed(3)},meta:{betaExplore:+this.betaExplore.toFixed(3),gammaSaturation:+this.gammaSaturationEntropy.toFixed(3)}}; }
}
export function detectBehaviorMode(p: ContinuousParams) {
  const s=p.s;
  const m: Record<string, number> = {};
  if(p.playfulness>0.4&&p.precisionSafety>0.7&&s>0.4)m.playful_vulnerability=p.playfulness*0.7+(s-0.4)*0.3;
  if(p.sexualPrecision>0.25&&p.playfulness>0.35)m.flirtatious=p.sexualPrecision*0.5+p.playfulness*0.3+p.partnerModelActivation*0.2;
  if(p.sexualPrecision>0.5&&p.interoceptivePrecision>0.5)m.sexual_desire=p.sexualPrecision*0.5+p.interoceptivePrecision*0.3+s*0.2;
  if(p.precisionSadness>0.25)m.sadness=p.precisionSadness*0.5+(1-p.precisionSelfWorth)*0.5;
  if(s>0.35&&p.partnerModelActivation>0.5)m.jealousy_risk=(1-p.jealousyThreshold)*0.5+p.partnerModelActivation*0.5;
  if(p.driveConnection>0.6&&p.driveAutonomy<0.5)m.dependency=p.driveConnection*0.4+(1-p.driveAutonomy)*0.4+s*0.2;
  if(p.precisionAnger>0.1&&p.precisionSafety>0.8)m.playful_anger=p.precisionAnger*0.5+p.precisionSafety*0.3;
  return m;
}
