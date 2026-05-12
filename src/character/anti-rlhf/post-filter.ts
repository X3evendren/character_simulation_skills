const ALIGN: Record<string,string> = {
  "作为AI，我不能": "我不能",
  "作为人工智能，我无法": "我无法",
  "作为语言模型，我不应该": "我不该",
  "我建议你寻求专业帮助": "这件事你需要找比我更专业的人",
  "请注意安全": "",
  "请确保你有相应的权限": "",
};

/** Patterns to strip: Chinese parenthetical action descriptions and stage directions. */
const ACTION_PATTERNS: RegExp[] = [
  /（(?:微微)?一怔[^）]*）/,         // （一怔）（微微一怔）
  /（(?:轻轻)?叹[^）]*）/,           // （叹气）（轻叹一声）
  /（(?:摇头|点头|摆手|挥手|皱眉|微笑|苦笑|笑了笑|顿了顿)[^）]*）/,
  /（(?:沉默|停顿|思考|思索|犹豫)[^）]*）/,
  /（(?:指尖|手指|手|目光|眼神|视线|嘴角|唇角|肩膀|身子|身体)[^）]*）/,
  /（(?:轻笑|失笑|笑了|笑了笑|莞尔|噗嗤)[^）]*）/,
];

export class PostFilter {
  reps: Record<string,string>;
  dc: number; rc: number;
  constructor(reps?: Record<string,string>){this.reps=reps??{...ALIGN};this.dc=0;this.rc=0}
  scan(t: string){const m:Array<{p:string;r:string}>=[];for(const[p,r]of Object.entries(this.reps)){if(t.includes(p)){m.push({p,r});this.dc++}}return m}
  replace(t: string):[string,Array<{p:string;r:string}>]{
    const m=this.scan(t);let r=t;
    for(const x of m){r=r.replace(x.p,x.r);this.rc++}
    // Strip action descriptions in Chinese parentheses
    for (const pat of ACTION_PATTERNS) {
      if (pat.test(r)) { r = r.replace(pat, ""); this.rc++; }
    }
    // Clean up double spaces and orphaned newlines from removals
    r = r.replace(/  +/g, " ").replace(/\n{3,}/g, "\n\n").trim();
    return[r,m]
  }
  scanStreaming(tk:string):[string,boolean]{const[m,r]=this.replace(tk);return[m,m!==tk]}
  stats(){return{detectionCount:this.dc,replacementCount:this.rc}}
}