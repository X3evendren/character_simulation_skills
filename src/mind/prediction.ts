import { MindState } from "../mind/state";

const FIELDS = ["pleasure","arousal","dominance","control","attachmentActivation","defenseStrength"];

export class PredictionTracker {
  windowSize: number;
  private h: MindState[];
  private ewma: Record<string,number>;
  private alpha: number;
  private lastErr: number;

  constructor(ws=10){this.windowSize=ws;this.h=[];this.ewma={};this.alpha=0.3;this.lastErr=0}

  predict(): MindState {
    if(!this.h.length)return new MindState();
    const l=this.h[this.h.length-1],p=new MindState();
    for(const f of FIELDS){const c=(l as any)[f]as number, e=this.ewma[f]??c, t=c-e; (p as any)[f]=Math.max(-1,Math.min(1,e+t*0.3))}
    return p
  }
  observe(a:MindState):number{
    for(const f of FIELDS){const v=(a as any)[f]as number, p=this.ewma[f]??v; this.ewma[f]=this.alpha*v+(1-this.alpha)*p}
    this.h.push(a.clone());if(this.h.length>this.windowSize)this.h=this.h.slice(-this.windowSize);
    if(this.h.length<2)return 0; const pred=this.predict(); this.lastErr=pred.distanceTo(a); return this.lastErr
  }
  computePredictionError(e:MindState,a:MindState):number{return e.distanceTo(a)}
  get surpriseLevel():number{return Math.min(1,this.lastErr)}
  get isSurprised():boolean{return this.lastErr>0.3}
}