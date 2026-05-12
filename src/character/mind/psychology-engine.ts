/** Psychology Engine — Single-model XML psychology analysis. 1:1 from core/psychology/engine.py */
import { MindState } from "./mind-state";
import { extractXML, extractXMLAttr } from "./json-parser";

export class EmotionResult { dominant = "neutral"; intensity = 0.5; pleasure = 0.0; arousal = 0.5; dominance = 0.0; nuance = ""; }
export class AttachmentResult { activation = 0.0; strategy = ""; }
export class DefenseResult { active = ""; intensity = 0.0; }
export class AppraisalResult { goalConduciveness = 0.0; copingPotential = 0.5; actionTendency = ""; }
export class MotivationResult { autonomy = 0.5; competence = 0.5; relatedness = 0.5; }
export class RelationResult { powerDynamic = "equal"; intimacy = 0.0; stability = 0.5; }

export class PsychologyResult {
  emotion = new EmotionResult(); attachment = new AttachmentResult();
  defense = new DefenseResult(); appraisal = new AppraisalResult();
  motivation = new MotivationResult(); relation = new RelationResult();
  innerMonologue = ""; parameterShifts: Record<string, number> = {};
  mindstate: Record<string, any> = {}; rawOutput = "";
}

export class PsychologyEngine {
  provider: any; model: string;

  constructor(provider: any, model = "") { this.provider = provider; this.model = model; }

  async analyze(
    event: Record<string, any>, memoryContext = "",
    currentMindstate?: MindState | null, driveState?: Record<string, any> | null,
    assistantConfig?: Record<string, string> | null,
  ): Promise<PsychologyResult> {
    const prompt = this._buildPrompt(event, memoryContext, currentMindstate, driveState, assistantConfig);
    try {
      const resp = await this.provider.chat(
        [{ role: "user", content: prompt }], 0.3, 2000, undefined, this.model,
      );
      return this._parseOutput(resp.content ?? "", currentMindstate ?? new MindState());
    } catch { return new PsychologyResult(); }
  }

  private _buildPrompt(
    event: Record<string, any>, memCtx: string, ms?: MindState | null,
    driveState?: Record<string, any> | null, config?: Record<string, string> | null,
  ): string {
    const m = ms ?? new MindState();
    let persona = "";
    if (config) persona = `你是 ${config.name ?? "助手"}。${config.essence ?? ""} ${config.traits ?? ""}`;

    let dt = "";
    if (driveState) {
      const d = driveState.desires ?? {};
      dt = Object.entries(d as Record<string, any>)
        .map(([k, v]: [string, any]) => `  ${k}: ${((v.intensity ?? 0.5) * 100).toFixed(0)}%`)
        .join("\n") || "未初始化";
    }

    return `${persona}

请以你的角色身份完成一次完整的心理分析。

【当前状态】
愉悦度: ${m.pleasure.toFixed(1)}  唤醒度: ${m.arousal.toFixed(1)}  支配感: ${m.dominance.toFixed(1)}
控制感: ${m.control.toFixed(1)}  防御强度: ${m.defenseStrength.toFixed(1)}

【驱力】
${dt}

【记忆】
${memCtx || "无"}

【事件】
${event.description ?? ""}

输出 XML:
<psychology>
  <emotion><dominant>情绪</dominant><intensity>0.5</intensity><pad pleasure="0" arousal="0.5" dominance="0"/><nuance>细腻描述</nuance></emotion>
  <attachment activation="0" strategy="secure"/>
  <defense active="无" intensity="0"/>
  <appraisal goal_conduciveness="0" coping_potential="0.5"/>
  <motivation autonomy="0.5" competence="0.5" relatedness="0.5"/>
  <relation power_dynamic="equal" intimacy="0" stability="0.5"/>
  <inner_monologue>内心想法</inner_monologue>
  <parameter_shifts><shift param="param" delta="+0.1"/></parameter_shifts>
</psychology>`;
  }

  private _parseOutput(raw: string, _ms: MindState): PsychologyResult {
    const r = new PsychologyResult(); r.rawOutput = raw;
    const pb = extractXML(raw, "psychology"); if (!pb) return r;

    const eb = extractXML(pb, "emotion");
    if (eb) {
      const d = extractXML(eb, "dominant") ?? "neutral";
      const istr = extractXML(eb, "intensity");
      const nu = extractXML(eb, "nuance") ?? "";
      let i = 0.5; if (istr) { const n = parseFloat(istr); if (!isNaN(n)) i = n; }
      const pad: any = { pleasure: 0.0, arousal: 0.5, dominance: 0.0 };
      for (const a of ["pleasure", "arousal", "dominance"]) {
        const v = extractXMLAttr(eb, "pad", a);
        if (v) { const n = parseFloat(v); if (!isNaN(n)) pad[a] = n; }
      }
      Object.assign(r.emotion, { dominant: d, intensity: i, pleasure: pad.pleasure, arousal: pad.arousal, dominance: pad.dominance, nuance: nu });
    }

    const aa = extractXMLAttr(pb, "attachment", "activation"), as = extractXMLAttr(pb, "attachment", "strategy");
    if (aa || as) Object.assign(r.attachment, { activation: aa ? parseFloat(aa) || 0 : 0, strategy: as ?? "" });

    const dn = extractXMLAttr(pb, "defense", "active"), di = extractXMLAttr(pb, "defense", "intensity");
    if (dn || di) Object.assign(r.defense, { active: dn ?? "无", intensity: di ? parseFloat(di) || 0 : 0 });

    const gc = extractXMLAttr(pb, "appraisal", "goal_conduciveness"), cp = extractXMLAttr(pb, "appraisal", "coping_potential");
    if (gc || cp) Object.assign(r.appraisal, { goalConduciveness: gc ? parseFloat(gc) || 0 : 0, copingPotential: cp ? parseFloat(cp) || 0.5 : 0.5 });

    const au = extractXMLAttr(pb, "motivation", "autonomy"), co = extractXMLAttr(pb, "motivation", "competence"), re = extractXMLAttr(pb, "motivation", "relatedness");
    if (au || co || re) Object.assign(r.motivation, { autonomy: au ? parseFloat(au) || 0.5 : 0.5, competence: co ? parseFloat(co) || 0.5 : 0.5, relatedness: re ? parseFloat(re) || 0.5 : 0.5 });

    const pd = extractXMLAttr(pb, "relation", "power_dynamic"), in_ = extractXMLAttr(pb, "relation", "intimacy"), st = extractXMLAttr(pb, "relation", "stability");
    if (pd || in_ || st) Object.assign(r.relation, { powerDynamic: pd ?? "equal", intimacy: in_ ? parseFloat(in_) || 0 : 0, stability: st ? parseFloat(st) || 0.5 : 0.5 });

    r.innerMonologue = extractXML(pb, "inner_monologue") ?? "";

    const sb = extractXML(pb, "parameter_shifts");
    if (sb) {
      const re = /<shift\s+param="(\w+)"\s+delta="([+-]?\d+\.?\d*)"/g;
      let m;
      while ((m = re.exec(sb)) !== null) { const v = parseFloat(m[2]); if (!isNaN(v)) r.parameterShifts[m[1]] = v; }
    }

    r.mindstate = {
      affect: { pleasure: r.emotion.pleasure, arousal: r.emotion.arousal, dominance: r.emotion.dominance },
      attachment_activation: r.attachment.activation,
      defense_strength: r.defense.intensity,
      control: r.appraisal.copingPotential,
    };
    return r;
  }
}
