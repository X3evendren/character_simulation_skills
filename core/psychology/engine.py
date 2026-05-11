"""心理推理引擎 — 单模型一次性完成全部心理学维度分析。

用一个独立的小模型（如 Haiku / GPT-4o-mini），单次 LLM 调用
输出完整的 XML 结构化心理分析，替代旧架构 24 个独立 Skill 类。

Token 预算: ~1500-2000 tokens（vs 旧架构 ~12000+）
延迟: 1 次 LLM 调用（vs 6-12 次串行调用）
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..provider import LLMProvider
from ..mind_state import MindState
from ..json_parser import extract_xml, extract_xml_attr


@dataclass
class EmotionResult:
    """情感分析结果"""
    dominant: str = "neutral"
    intensity: float = 0.5
    pleasure: float = 0.0
    arousal: float = 0.5
    dominance: float = 0.0
    nuance: str = ""


@dataclass
class AttachmentResult:
    """依恋分析结果"""
    activation: float = 0.0
    strategy: str = ""


@dataclass
class DefenseResult:
    """防御机制分析结果"""
    active: str = ""
    intensity: float = 0.0


@dataclass
class AppraisalResult:
    """认知评估结果"""
    goal_conduciveness: float = 0.0
    coping_potential: float = 0.5
    action_tendency: str = ""


@dataclass
class MotivationResult:
    """动机分析结果 (SDT)"""
    autonomy: float = 0.5
    competence: float = 0.5
    relatedness: float = 0.5


@dataclass
class RelationResult:
    """关系评估结果"""
    power_dynamic: str = "equal"
    intimacy: float = 0.0
    stability: float = 0.5


@dataclass
class PsychologyResult:
    """单次心理分析完整结果"""
    emotion: EmotionResult = field(default_factory=EmotionResult)
    attachment: AttachmentResult = field(default_factory=AttachmentResult)
    defense: DefenseResult = field(default_factory=DefenseResult)
    appraisal: AppraisalResult = field(default_factory=AppraisalResult)
    motivation: MotivationResult = field(default_factory=MotivationResult)
    relation: RelationResult = field(default_factory=RelationResult)
    inner_monologue: str = ""
    parameter_shifts: dict[str, float] = field(default_factory=dict)  # param_name → delta
    mindstate: dict = field(default_factory=dict)
    raw_output: str = ""


class PsychologyEngine:
    """心理推理引擎 — 同一 Provider 的小模型一次性完成全部分析。

    用法:
        engine = PsychologyEngine(provider, model="gpt-4o-mini")
        result = await engine.analyze(event, memory_context, mindstate, drive_state)
        # result.emotion.dominant → "anxiety"
        # result.inner_monologue → "他在犹豫，我能感觉到"
    """

    def __init__(self, provider: LLMProvider, model: str = ""):
        self.provider = provider
        self.model = model  # 如果为空，使用 provider 的默认模型

    async def analyze(
        self,
        event: dict,
        memory_context: str = "",
        current_mindstate: MindState | None = None,
        drive_state: dict | None = None,
        assistant_config: dict | None = None,
    ) -> PsychologyResult:
        """执行一次心理分析——单次 LLM 调用，输出 XML 结构。

        Args:
            event: {"description": "...", "type": "social", "significance": 0.5, ...}
            memory_context: 从记忆系统检索到的上下文文本
            current_mindstate: 当前 MindState
            drive_state: 当前驱力状态
            assistant_config: assistant.md 解析后的配置

        Returns:
            PsychologyResult: 完整的心理分析结果
        """
        prompt = self._build_prompt(event, memory_context, current_mindstate,
                                     drive_state, assistant_config)

        ms = current_mindstate or MindState()

        try:
            response = await self.provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            raw = response.content
        except Exception:
            return PsychologyResult(raw_output="")

        return self._parse_output(raw, ms)

    def _build_prompt(self, event, memory_context, mindstate, drive_state, config) -> str:
        """构建心理分析 Prompt。

        将角色人设、记忆上下文、当前状态、驱力状态注入 prompt，
        要求 LLM 一次性完成全部心理学维度的 XML 结构化输出。
        """
        ms = mindstate or MindState()

        # 角色人设
        persona = ""
        if config:
            name = config.get("name", "助手")
            persona = f"你是 {name}。{config.get('essence', '')} {config.get('traits', '')}"

        # 驱力上下文
        drive_text = ""
        if drive_state:
            desires = drive_state.get("desires", {})
            drive_lines = [f"  {k}: {v.get('intensity', 0.5):.0%}" for k, v in desires.items()]
            drive_text = "\n".join(drive_lines) if drive_lines else "驱力状态未初始化"

        prompt = f"""{persona}

你正在经历一个事件。请以你的角色身份，完成一次完整的心理分析。
分析你内心的真实感受——包括你可能不愿意承认的部分。

【当前状态】
愉悦度: {ms.pleasure:.1f}  唤醒度: {ms.arousal:.1f}  支配感: {ms.dominance:.1f}
控制感: {ms.control:.1f}  防御强度: {ms.defense_strength:.1f}

【驱力状态】
{drive_text}

【相关记忆】
{memory_context or '无相关记忆'}

【当前事件】
{event.get('description', '')}

请用以下 XML 格式输出你的完整心理分析。只输出 XML，不要其他内容:

<psychology>
  <emotion>
    <dominant>主导情绪(anger/sadness/fear/joy/trust/disgust/surprise/anticipation)</dominant>
    <intensity>0.0-1.0</intensity>
    <pad pleasure="-1.0到1.0" arousal="0.0到1.0" dominance="-1.0到1.0"/>
    <nuance>更细腻的情感描述(中文，一句话)</nuance>
  </emotion>
  <attachment activation="0.0-1.0" strategy="secure/seeking_reassurance/distancing/push_pull"/>
  <defense active="无或防御机制名称" intensity="0.0-1.0"/>
  <appraisal goal_conduciveness="-1.0到1.0" coping_potential="0.0-1.0"/>
  <motivation autonomy="0.0-1.0" competence="0.0-1.0" relatedness="0.0-1.0"/>
  <relation power_dynamic="dominant/submissive/equal" intimacy="0.0-1.0" stability="0.0-1.0"/>
  <inner_monologue>你此刻内心的真实想法，包括你可能不会说出口的</inner_monologue>
  <parameter_shifts>
    <!-- 只输出本回合有变化的参数。正值=激活/上升，负值=降低/衰减 -->
    <!-- activation (快分量): joy sadness fear anger disgust surprise trust anticipation -->
    <!-- PAD: pleasure arousal dominance -->
    <!-- 认知: goal_conduciveness coping_potential unexpectedness certainty urgency -->
    <!-- 关系: passion sexual_activation playfulness intimacy_activation -->
    <!-- 防御: defense_intensity threat_precision safety_precision attachment_activation -->
    <!-- 动机: relatedness -->
    <!-- 自我: self_worth_activation self_update_openness -->
    <shift param="anger" delta="-0.15"/>
    <shift param="sadness" delta="+0.40"/>
    <shift param="threat_precision" delta="+0.30"/>
    <!-- 没有变化的参数不需要输出 -->
  </parameter_shifts>
</psychology>"""
        return prompt

    def _parse_output(self, raw: str, ms: MindState) -> PsychologyResult:
        """解析 LLM 输出的 XML 结构。"""
        result = PsychologyResult(raw_output=raw)

        # 提取 <psychology> 块
        psych_block = extract_xml(raw, "psychology")
        if not psych_block:
            return result

        # <emotion>
        emotion_block = extract_xml(psych_block, "emotion")
        if emotion_block:
            dominant = extract_xml(emotion_block, "dominant") or "neutral"
            intensity_str = extract_xml(emotion_block, "intensity")
            pad_block = extract_xml(emotion_block, "pad")
            nuance = extract_xml(emotion_block, "nuance") or ""

            intensity = 0.5
            if intensity_str:
                try:
                    intensity = float(intensity_str)
                except ValueError:
                    pass

            pad = {"pleasure": 0.0, "arousal": 0.5, "dominance": 0.0}
            if pad_block:
                for attr in ["pleasure", "arousal", "dominance"]:
                    val = extract_xml_attr(emotion_block, "pad", attr)
                    if val:
                        try:
                            pad[attr] = float(val)
                        except ValueError:
                            pass

            result.emotion = EmotionResult(
                dominant=dominant, intensity=intensity,
                pleasure=pad["pleasure"], arousal=pad["arousal"],
                dominance=pad["dominance"], nuance=nuance,
            )

        # <attachment>
        att_activation = extract_xml_attr(psych_block, "attachment", "activation")
        att_strategy = extract_xml_attr(psych_block, "attachment", "strategy")
        if att_activation or att_strategy:
            result.attachment = AttachmentResult(
                activation=float(att_activation) if att_activation else 0.0,
                strategy=att_strategy or "",
            )

        # <defense>
        def_name = extract_xml_attr(psych_block, "defense", "active")
        def_intensity = extract_xml_attr(psych_block, "defense", "intensity")
        if def_name or def_intensity:
            result.defense = DefenseResult(
                active=def_name or "无",
                intensity=float(def_intensity) if def_intensity else 0.0,
            )

        # <appraisal>
        gc = extract_xml_attr(psych_block, "appraisal", "goal_conduciveness")
        cp = extract_xml_attr(psych_block, "appraisal", "coping_potential")
        if gc or cp:
            result.appraisal = AppraisalResult(
                goal_conduciveness=float(gc) if gc else 0.0,
                coping_potential=float(cp) if cp else 0.5,
            )

        # <motivation>
        auto = extract_xml_attr(psych_block, "motivation", "autonomy")
        comp = extract_xml_attr(psych_block, "motivation", "competence")
        rel = extract_xml_attr(psych_block, "motivation", "relatedness")
        if auto or comp or rel:
            result.motivation = MotivationResult(
                autonomy=float(auto) if auto else 0.5,
                competence=float(comp) if comp else 0.5,
                relatedness=float(rel) if rel else 0.5,
            )

        # <relation>
        pd = extract_xml_attr(psych_block, "relation", "power_dynamic")
        intimacy = extract_xml_attr(psych_block, "relation", "intimacy")
        stability = extract_xml_attr(psych_block, "relation", "stability")
        if pd or intimacy or stability:
            result.relation = RelationResult(
                power_dynamic=pd or "equal",
                intimacy=float(intimacy) if intimacy else 0.0,
                stability=float(stability) if stability else 0.5,
            )

        # <inner_monologue>
        result.inner_monologue = extract_xml(psych_block, "inner_monologue") or ""

        # <parameter_shifts> —— 解析 LLM 输出的参数调制
        shifts_block = extract_xml(psych_block, "parameter_shifts")
        if shifts_block:
            import re as _re
            for match in _re.finditer(
                r'<shift\s+param="(\w+)"\s+delta="([+-]?\d+\.?\d*)"',
                shifts_block
            ):
                try:
                    result.parameter_shifts[match.group(1)] = float(match.group(2))
                except ValueError:
                    pass

        # 构建 MindState 更新
        result.mindstate = {
            "affect": {
                "pleasure": result.emotion.pleasure,
                "arousal": result.emotion.arousal,
                "dominance": result.emotion.dominance,
            },
            "attachment_activation": result.attachment.activation,
            "defense_strength": result.defense.intensity,
            "control": result.appraisal.coping_potential,
        }

        return result
