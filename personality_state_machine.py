"""人格状态机 — Dynamic Personality States

基于 Dynamic State Machines (Pielage et al., 2026) 和
The Personality Illusion (NeurIPS 2025):

挑战: 静态OCEAN不能捕捉角色在不同情境下的人格变化。
- 洛玉伶在公共场合: 高支配/低神经质（圣姑面具）
- 洛玉伶在主角面前: 低支配/高神经质（秘密被掌握的恐惧）
- 洛玉伶独处时: 高神经质/低外向（反思/焦虑）

解决方案: 人格状态机
- OCEAN基线 → 情境化OCEAN状态
- 状态转移由 event_type + emotional_state 驱动
- 每个状态有独立的OCEAN偏置
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OCEANProfile:
    """OCEAN人格五维度"""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    def to_dict(self) -> dict:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OCEANProfile":
        return cls(
            openness=d.get("openness", 0.5),
            conscientiousness=d.get("conscientiousness", 0.5),
            extraversion=d.get("extraversion", 0.5),
            agreeableness=d.get("agreeableness", 0.5),
            neuroticism=d.get("neuroticism", 0.5),
        )


# 情境人格状态定义
PERSONALITY_STATES = {
    "baseline": {       # 默认基线
        "description": "角色独处或日常状态下的真实人格",
        "bias": {},
    },
    "social_public": {  # 公开社交
        "description": "角色在有观众/公开场合的表现",
        "bias": {"extraversion": 0.10, "neuroticism": -0.10, "agreeableness": 0.05},
    },
    "conflict": {       # 冲突/对抗
        "description": "角色面对威胁/挑战时的状态",
        "bias": {"agreeableness": -0.15, "neuroticism": 0.10, "extraversion": 0.05},
    },
    "romantic_intimate": {  # 亲密关系
        "description": "角色与伴侣/亲近者独处时的状态",
        "bias": {"neuroticism": 0.10, "agreeableness": 0.10, "extraversion": -0.05},
    },
    "threat_fear": {    # 恐惧/威胁
        "description": "角色面对危险/安全威胁时的状态",
        "bias": {"neuroticism": 0.20, "agreeableness": -0.05, "openness": -0.05},
    },
    "triumph_success": {  # 成功/胜利
        "description": "角色取得成就/胜利后的状态",
        "bias": {"extraversion": 0.15, "neuroticism": -0.15, "agreeableness": 0.05},
    },
    "loss_defeat": {    # 失败/失去
        "description": "角色遭受挫折/失去后的状态",
        "bias": {"neuroticism": 0.20, "extraversion": -0.15, "openness": -0.05},
    },
    "authority_submission": {  # 面对权威
        "description": "角色面对更高权力者时的状态",
        "bias": {"agreeableness": 0.15, "neuroticism": 0.05, "extraversion": -0.10},
    },
    "moral_dilemma": {  # 道德困境
        "description": "角色面对道德选择时的状态",
        "bias": {"openness": 0.05, "neuroticism": 0.10, "conscientiousness": 0.05},
    },
}


@dataclass
class PersonalityStateMachine:
    """人格状态机

    维护角色的OCEAN基线和当前激活的情境人格状态。
    状态转移由事件类型和情绪状态驱动。
    """
    baseline: OCEANProfile = field(default_factory=OCEANProfile)
    current_state: str = "baseline"
    previous_state: str = "baseline"

    def get_active_profile(self) -> OCEANProfile:
        """获取当前情境下的实际OCEAN profile"""
        state_def = PERSONALITY_STATES.get(self.current_state, PERSONALITY_STATES["baseline"])
        biases = state_def.get("bias", {})

        profile = OCEANProfile(
            openness=self._clamp(self.baseline.openness + biases.get("openness", 0)),
            conscientiousness=self._clamp(self.baseline.conscientiousness + biases.get("conscientiousness", 0)),
            extraversion=self._clamp(self.baseline.extraversion + biases.get("extraversion", 0)),
            agreeableness=self._clamp(self.baseline.agreeableness + biases.get("agreeableness", 0)),
            neuroticism=self._clamp(self.baseline.neuroticism + biases.get("neuroticism", 0)),
        )
        return profile

    def update_state(self, event_type: str, emotional_state: dict, has_authority: bool = False) -> str:
        """根据事件类型和情绪状态更新当前人格状态。

        返回状态转移描述。
        """
        self.previous_state = self.current_state
        new_state = self._determine_state(event_type, emotional_state, has_authority)
        self.current_state = new_state
        return f"{self.previous_state} → {self.current_state}"

    def _determine_state(self, event_type: str, emotional_state: dict, has_authority: bool) -> str:
        """状态判定逻辑"""
        dominant = emotional_state.get("dominant", "")
        pleasantness = emotional_state.get("pleasantness", 0)
        arousal = emotional_state.get("intensity", 0.5)

        # 道德困境
        if event_type in ("moral_choice", "moral_dilemma"):
            return "moral_dilemma"

        # 权威情境
        if has_authority:
            return "authority_submission"

        # 浪漫/亲密
        if event_type in ("romantic", "confession", "intimate"):
            return "romantic_intimate"

        # 冲突
        if event_type in ("conflict", "battle", "confrontation", "argument", "betrayal"):
            return "conflict"

        # 情绪驱动的转移
        if dominant in ("fear",) or pleasantness < -0.5:
            return "threat_fear"
        if dominant in ("joy",) and pleasantness > 0.5:
            return "triumph_success"
        if dominant in ("sadness",) and pleasantness < -0.3:
            return "loss_defeat"

        # 社交情境
        if event_type in ("social", "public", "gathering", "ceremony"):
            return "social_public"

        return "baseline"

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def get_state_description(self) -> str:
        return PERSONALITY_STATES.get(self.current_state, {}).get(
            "description", "未知状态"
        )

    def micro_update(self, partner_emotion: dict, partner_power_move: str = "",
                     topic_keywords: list[str] | None = None) -> dict:
        """轮次级人格状态微调 — 在每次对方说完话后调用.

        Args:
            partner_emotion: 对方当前的情感状态 {dominant, intensity, pleasantness}
            partner_power_move: 对方的权力动作类型
                ("dominate" 支配, "submit" 顺从, "threaten" 威胁,
                 "appeal" 恳求, "probe" 试探, "neutral" 中性)
            topic_keywords: 当前对话涉及的话题关键词

        Returns:
            本轮的人格微调描述
        """
        changes = {}

        # 1. 话题驱动的情感记忆触发
        if topic_keywords:
            triggers = getattr(self, '_emotional_triggers', {})
            for keyword in topic_keywords:
                if keyword in triggers:
                    trigger_effect = triggers[keyword]
                    # 应用触发效果（累积，但不超过合理范围）
                    for trait, delta in trigger_effect.items():
                        old = getattr(self.baseline, trait)
                        # 微调幅度限制在±0.15
                        clamped_delta = max(-0.15, min(0.15, delta))
                        new_val = self._clamp(old + clamped_delta)
                        setattr(self.baseline, trait, new_val)
                        changes[trait] = new_val - old

        # 2. 对方权力动作驱动的状态调整
        power_responses = {
            "dominate": {"neuroticism": 0.03, "extraversion": -0.02},  # 被压制→略焦虑，更内敛
            "threaten": {"neuroticism": 0.05, "agreeableness": 0.03},  # 被威胁→焦虑+略顺从
            "submit": {"extraversion": 0.03, "dominance_shift": 0.05}, # 对方顺从→更敢表达
            "appeal": {"agreeableness": 0.03, "neuroticism": -0.02},    # 被恳求→略软化，略放松
            "probe": {"neuroticism": 0.02},                              # 被试探→略紧张
            "neutral": {},
        }
        if partner_power_move in power_responses:
            for trait, delta in power_responses[partner_power_move].items():
                if trait == "dominance_shift":
                    continue  # 仅用于状态判断，不修改OCEAN
                old = getattr(self.baseline, trait)
                new_val = self._clamp(old + delta * 0.5)  # 微调幅度折半
                setattr(self.baseline, trait, new_val)
                if abs(new_val - old) > 0.001:
                    changes[trait] = changes.get(trait, 0) + (new_val - old)

        # 3. 对方情绪驱动的共情调整
        partner_dominant = partner_emotion.get("dominant", "")
        partner_intensity = partner_emotion.get("intensity", 0.5)

        emotion_contagion = {
            "anger": {"neuroticism": 0.02, "agreeableness": -0.02},   # 对方生气→略紧张、略强硬
            "fear": {"agreeableness": 0.02, "neuroticism": 0.01},      # 对方害怕→略保护欲、略紧张
            "sadness": {"agreeableness": 0.03, "neuroticism": -0.01},  # 对方悲伤→更温和
            "joy": {"extraversion": 0.02, "neuroticism": -0.02},       # 对方开心→更开朗
        }
        if partner_dominant in emotion_contagion:
            for trait, delta in emotion_contagion[partner_dominant].items():
                scaled_delta = delta * partner_intensity * 0.5
                old = getattr(self.baseline, trait)
                new_val = self._clamp(old + scaled_delta)
                setattr(self.baseline, trait, new_val)
                if abs(new_val - old) > 0.001:
                    changes[trait] = changes.get(trait, 0) + (new_val - old)

        # 返回本轮调整的摘要
        if changes:
            change_desc = ", ".join(
                f"{k}{'+' if v>0 else ''}{v:.3f}" for k, v in changes.items()
            )
            return {"micro_updated": True, "changes": changes, "summary": change_desc}
        return {"micro_updated": False, "changes": {}}

    def set_emotional_triggers(self, triggers: dict) -> None:
        """设置话题→OCEAN偏置的情感记忆触发器.

        示例:
            psm.set_emotional_triggers({
                "范闲": {"openness": 0.05, "agreeableness": 0.10},
                "叶轻眉": {"openness": 0.15, "neuroticism": -0.10},
            })
        当对话中出现这些关键词时，micro_update自动触发OCEAN偏移。
        """
        self._emotional_triggers = triggers

    def to_dict(self) -> dict:
        return {
            "baseline": self.baseline.to_dict(),
            "current_state": self.current_state,
            "previous_state": self.previous_state,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PersonalityStateMachine":
        return cls(
            baseline=OCEANProfile.from_dict(d.get("baseline", {})),
            current_state=d.get("current_state", "baseline"),
            previous_state=d.get("previous_state", "baseline"),
        )
