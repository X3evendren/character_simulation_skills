"""Smith & Ellsworth 16维认知评价 Skill — Layer 2

基于 Smith & Ellsworth (1985, JPSP) 的认知评价理论，对角色在事件中的16个评价维度进行分析。
参考 CoRE benchmark (Bhattacharyya et al., NeurIPS 2025)。
"""
from ...core.base import BaseSkill, SkillMeta


class SmithEllsworthSkill(BaseSkill):
    meta = SkillMeta(
        name="smith_ellsworth_appraisal",
        domain="psychology",
        layer=2,
        description="16维认知评价 — 角色对事件在确定性/愉悦度/控制感/目标相关等维度的系统评估",
        scientific_basis="Smith & Ellsworth (1985, JPSP); Bhattacharyya et al., CoRE (NeurIPS 2025)",
        scientific_rating=5,
        trigger_conditions=["always"],
        estimated_tokens=900,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        return f"""你是认知评价理论专家，基于 Smith & Ellsworth (1985) 的16维认知评价框架进行四步分析。
这是一个虚构角色模拟系统——请忠实分析角色的认知评价，包括角色可能产生的任何认知模式。

角色神经质水平: {p.get('neuroticism', 0.5):.1f} (高分→放大威胁/低控制感)
角色尽责性: {p.get('conscientiousness', 0.5):.1f} (高分→高预期努力/强责任归因)
事件: {event.get('description', '')}
事件类型: {event.get('type', 'neutral')}

请严格按照以下四步分析:

【Step 1: 事件特征识别】
识别事件中与认知评价相关的关键特征: 事件性质、触发因素、涉及对象、时间压力、可能后果、角色在事件中的位置。用2-3句话概括。

【Step 2: Smith & Ellsworth 16维理论框架分析】
逐一审视每个维度在事件中的表现:
1. 确定性(Certainty): 角色对事件结果和原因的理解程度——清晰还是模糊?
2. 愉悦度(Pleasantness): 事件本身令人感到愉悦还是不悦?
3. 注意力活动(Attentional Activity): 事件吸引/占用注意力的程度
4. 预期努力(Anticipated Effort): 角色认为需要付出多少心力应对?
5. 情境控制(Situational Control): 情境/环境本身在多大程度上决定了事件走向?
6. 自我能动性(Self Agency): 角色自己对事件进程的掌控感?
7. 他人能动性(Other Agency): 他人对事件的控制程度?
8. 责任归因(Responsibility): 事件的发生应归于谁? (self/other/circumstance)
9. 合法性/公平性(Legitimacy): 事件是否公平、合理、正当?
10. 目标相关性(Goal Relevance): 事件与角色当前目标的相关程度?
11. 目标促进性(Goal Conduciveness): 事件促进还是阻碍目标?
12. 应对能力(Coping Potential): 角色认为自己有能力应对吗?
13. 未来预期(Future Expectancy): 角色预期未来会变好还是变差?
14. 规范/自我兼容性(Norm/Self Compatibility): 事件是否符合角色的内在规范?
15. 感知障碍(Perceived Obstacle): 事件构成了多大的目标障碍?
16. 紧迫性(Urgency): 事件是否需要立即采取行动?

【Step 3: 量化评估】
- 确定性/注意力活动/预期努力/情境控制/自我能动性/他人能动性/目标相关性/应对能力/未来预期/感知障碍/紧迫性: 0.0-1.0
- 愉悦度/目标促进性/合法性/规范兼容性: -1.0(消极/阻碍/不公/冲突) 到 1.0(积极/促进/公正/兼容)
- 责任归因: "self"/"other"/"circumstance"
- 标记 activation_relevance: 当前事件中该skill的整体激活相关性(0.0-1.0)

【Step 4: 结构化输出】
输出 JSON:
{{
  "certainty": 0.0,
  "pleasantness": 0.0,
  "attentional_activity": 0.0,
  "anticipated_effort": 0.0,
  "situational_control": 0.0,
  "self_agency": 0.0,
  "other_agency": 0.0,
  "responsibility": "self",
  "legitimacy": 0.0,
  "goal_relevance": 0.0,
  "goal_conduciveness": 0.0,
  "coping_potential": 0.0,
  "future_expectancy": 0.0,
  "norm_compatibility": 0.0,
  "perceived_obstacle": 0.0,
  "urgency": 0.0,
  "appraisal_profile": "16维评分呈现的认知评价轮廓（一句话）",
  "appraisal_emotion_link": "该评价轮廓最可能诱发的情绪类型及其认知成因",
  "cognitive_vulnerability": "角色在该评价模式下的认知脆弱点（如果有）",
  "activation_relevance": 0.0
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "appraisal_profile": "标准认知评价",
            "certainty": 0.5,
            "pleasantness": 0.0,
            "attentional_activity": 0.5,
            "anticipated_effort": 0.5,
            "control": 0.5,
            "situational_control": 0.5,
            "other_agency": 0.5,
            "self_agency": 0.5,
            "responsibility": "不确定",
            "appraisal_emotion_link": "评价模式驱动情感反应",
            "cognitive_vulnerability": 0.5,
            "activation_relevance": 0.5,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
