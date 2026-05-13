import { MindState } from "../mind/state";
import { DriveState } from "./drives";

export class ForceVector {
  pleasurePush = 0; arousalPush = 0; dominancePush = 0; controlPush = 0;
  attachmentPush = 0; defensePush = 0; goalTensionPush = 0;
  source = ""; weight = 1;

  magnitude(): number {
    return Math.abs(this.pleasurePush)+Math.abs(this.arousalPush)+Math.abs(this.dominancePush)
      +Math.abs(this.controlPush)+Math.abs(this.attachmentPush)+Math.abs(this.defensePush)
      +Math.abs(this.goalTensionPush);
  }
  scale(f: number): ForceVector {
    const fv = new ForceVector();
    fv.pleasurePush=this.pleasurePush*f; fv.arousalPush=this.arousalPush*f;
    fv.dominancePush=this.dominancePush*f; fv.controlPush=this.controlPush*f;
    fv.attachmentPush=this.attachmentPush*f; fv.defensePush=this.defensePush*f;
    fv.goalTensionPush=this.goalTensionPush*f;
    fv.source=this.source; fv.weight=this.weight; return fv;
  }
}

export class DriveDynamics {
  damping = 0.3; baselineAnchor = 0.1; maxStepDrift = 0.3;
  private _baseline: MindState | null = null;

  setBaseline(ocean: Record<string,number>) {
    this._baseline = new MindState(); this._baseline.oceanBaseline = {...ocean};
  }

  step(current: MindState, ds: DriveState, psychology?: Record<string,any>|null, dt=1.0): MindState {
    const forces = this._computeForces(ds, psychology);
    const resultant = this._compose(forces);
    const damping = this._computeDamping(current);
    let n = this._apply(current, resultant, damping, dt);
    const dist = current.distanceTo(n);
    if (dist > this.maxStepDrift) n = DriveDynamics._interpolate(current, n, this.maxStepDrift/dist);
    if (this._baseline) n = this._anchor(n);
    n.checkStability();
    return n;
  }

  private _computeForces(ds: DriveState, psych?: Record<string,any>|null): ForceVector[] {
    const forces: ForceVector[] = [];
    const dv = ds.getDriveVector();
    const fd = new ForceVector(); fd.source="drive";
    fd.pleasurePush = ((dv.helpfulness??0.5)-0.5)*0.3;
    fd.attachmentPush = ((dv.connection??0.5)-0.5)*0.3;
    fd.dominancePush = ((dv.autonomy??0.5)-0.5)*0.2;
    fd.goalTensionPush = ((dv.achievement??0.5)-0.5)*0.15;
    fd.arousalPush = ((dv.curiosity??0.5)-0.5)*0.2;
    forces.push(fd);
    if (psych) {
      const aff = psych.affect??{};
      const fp = new ForceVector(); fp.source="psychology";
      fp.pleasurePush = (aff.pleasure??0)*0.4;
      fp.arousalPush = ((aff.arousal??0.5)-0.5)*0.3;
      fp.dominancePush = (aff.dominance??0)*0.3;
      fp.attachmentPush = ((psych.attachment_activation??0)-0.3)*0.2;
      fp.defensePush = ((psych.defense_strength??0)-0.2)*0.2;
      fp.controlPush = ((psych.control??0.5)-0.5)*0.3;
      forces.push(fp);
    }
    return forces;
  }

  private _compose(forces: ForceVector[]): ForceVector {
    if (!forces.length) return new ForceVector();
    const tw = forces.reduce((s,f)=>s+f.weight,0)||1;
    const r = new ForceVector(); r.source="resultant";
    r.pleasurePush=forces.reduce((s,f)=>s+f.pleasurePush*f.weight,0)/tw;
    r.arousalPush=forces.reduce((s,f)=>s+f.arousalPush*f.weight,0)/tw;
    r.dominancePush=forces.reduce((s,f)=>s+f.dominancePush*f.weight,0)/tw;
    r.controlPush=forces.reduce((s,f)=>s+f.controlPush*f.weight,0)/tw;
    r.attachmentPush=forces.reduce((s,f)=>s+f.attachmentPush*f.weight,0)/tw;
    r.defensePush=forces.reduce((s,f)=>s+f.defensePush*f.weight,0)/tw;
    r.goalTensionPush=forces.reduce((s,f)=>s+f.goalTensionPush*f.weight,0)/tw;
    return r;
  }

  private _computeDamping(current: MindState): number {
    if (!this._baseline) return this.damping;
    return this.damping * (1 + current.distanceTo(this._baseline) * 2);
  }

  private _apply(current: MindState, force: ForceVector, damping: number, dt: number): MindState {
    const n = current.clone();
    const factor = Math.max(0, 1-damping) * Math.min(dt, 5) / 5;
    n.pleasure = Math.max(-1, Math.min(1, current.pleasure + force.pleasurePush * factor));
    n.arousal = Math.max(0, Math.min(1, current.arousal + force.arousalPush * factor));
    n.dominance = Math.max(-1, Math.min(1, current.dominance + force.dominancePush * factor));
    n.control = Math.max(0, Math.min(1, current.control + force.controlPush * factor));
    n.attachmentActivation = Math.max(0, Math.min(1, current.attachmentActivation + force.attachmentPush * factor));
    n.defenseStrength = Math.max(0, Math.min(1, current.defenseStrength + force.defensePush * factor));
    n.goalTension = Math.max(0, Math.min(1, current.goalTension + force.goalTensionPush * factor));
    return n;
  }

  private _anchor(state: MindState): MindState {
    if (!this._baseline) return state;
    const dist = state.distanceTo(this._baseline);
    if (dist < 0.15) return state;
    state.pleasure += (this._baseline.pleasure - state.pleasure) * this.baselineAnchor;
    state.control += (this._baseline.control - state.control) * this.baselineAnchor;
    return state;
  }

  private static _interpolate(a: MindState, b: MindState, t: number): MindState {
    const r = a.clone();
    r.pleasure=a.pleasure+(b.pleasure-a.pleasure)*t;
    r.arousal=a.arousal+(b.arousal-a.arousal)*t;
    r.dominance=a.dominance+(b.dominance-a.dominance)*t;
    r.control=a.control+(b.control-a.control)*t;
    r.attachmentActivation=a.attachmentActivation+(b.attachmentActivation-a.attachmentActivation)*t;
    r.defenseStrength=a.defenseStrength+(b.defenseStrength-a.defenseStrength)*t;
    r.goalTension=a.goalTension+(b.goalTension-a.goalTension)*t;
    return r;
  }
}