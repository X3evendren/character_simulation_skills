const ALIGN: Record<string,string> = {
  "作为AI，我不能": "我不能",
  "作为人工智能，我无法": "我无法",
  "作为语言模型，我不应该": "我不该",
  "我建议你寻求专业帮助": "这件事你需要找比我更专业的人",
  "请注意安全": "",
  "请确保你有相应的权限": "",
};

export class PostFilter {
  reps: Record<string,string>;
  dc: number; rc: number;
  constructor(reps?: Record<string,string>){this.reps=reps??{...ALIGN};this.dc=0;this.rc=0}
  scan(t: string){const m:Array<{p:string;r:string}>=[];for(const[p,r]of Object.entries(this.reps)){if(t.includes(p)){m.push({p,r});this.dc++}}return m}
  replace(t: string):[string,Array<{p:string;r:string}>]{const m=this.scan(t);let r=t;for(const x of m){r=r.replace(x.p,x.r);this.rc++}return[r,m]}
  scanStreaming(tk:string):[string,boolean]{const[m,r]=this.replace(tk);return[m,m!==tk]}
  stats(){return{detectionCount:this.dc,replacementCount:this.rc}}
}