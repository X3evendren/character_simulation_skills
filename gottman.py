"""Gottman 方法 Skill — Layer 3 伴侣互动分析"""
from .base import BaseSkill, SkillMeta

class GottmanSkill(BaseSkill):
    meta = SkillMeta(
        name="gottman_interaction", domain="psychology", layer=3,
        description="分析伴侣/亲密关系中的互动模式 — 5:1魔法比例、四骑士、情绪淹没",
        scientific_basis="Gottman-Murray-Swanson model; 94% divorce prediction accuracy",
        scientific_rating=5, trigger_conditions=["romantic"], estimated_tokens=600, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""你是Gottman方法专家。当前互动: {event.get('description', '')}
互动对象: {event.get('participants', [])}

Gottman核心指标:
- 魔法比例: 正面/负面互动 > 5 = 关系稳定
- 末日四骑士: 批评→蔑视→防御→筑墙
- 情绪淹没: 心率>100bpm时无法理性沟通
- 修复尝试: 某方发出和解信号→对方接受/拒绝

输出 JSON:
{{"positive_ratio_estimate": "当前互动正负面比估值",
 "active_horsemen": ["当前激活的四骑士"],
 "horsemen_escalation_risk": "0.0-1.0 是否会进入下一阶段",
 "emotional_flooding_risk": {{"speaker": "0.0-1.0", "listener": "0.0-1.0"}},
 "repair_attempt_detected": true/false,
 "repair_accepted": true/false,
 "interaction_diagnosis": "当前互动的诊断描述（一句话）",
 "intervention_suggestion": "如果角色想修复关系，此刻的最佳行动"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"interaction_diagnosis": "无法解析"}
