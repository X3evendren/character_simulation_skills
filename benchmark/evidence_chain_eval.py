"""Evidence Chain Evaluation — 三条证据链评估。

借鉴 Claw-Eval 的三条证据链思路：
- Chain A (Dialogue History): 回应是否从对话上下文逻辑推导？
- Chain B (State Changes): 情感/人格状态转换是否与回应一致？
- Chain C (Emotion Trajectory): 跨越 3+ 事件的情感弧线是否连贯？

几何平均 closure_score——单一弱链拉低整体分数。
零额外 token 成本——纯数学计算。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class EvidenceChainResult:
    """单条证据链的评估结果。"""
    chain_type: str          # "dialogue" / "state" / "trajectory"
    score: float             # 1.0-5.0
    gaps: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class EvidenceChainJudge:
    """三条证据链评估器。"""

    history_window: int = 3        # 对话历史窗口
    trajectory_window: int = 5     # 情感轨迹窗口
    emotion_continuity_weight: float = 0.4
    state_consistency_weight: float = 0.35
    dialogue_coherence_weight: float = 0.25

    def evaluate(
        self, event: dict, response: dict,
        dialogue_history: list[dict] | None = None,
        state_before: dict | None = None,
        state_after: dict | None = None,
        emotion_history: list[dict] | None = None,
    ) -> dict:
        """运行三条证据链评估。"""
        chain_a = self._eval_dialogue_coherence(response, dialogue_history or [])
        chain_b = self._eval_state_consistency(response, state_before, state_after)
        chain_c = self._eval_emotion_trajectory(emotion_history or [])

        scores = [chain_a.score, chain_b.score, chain_c.score]
        closure = _geometric_mean(scores)

        return {
            "closure_score": round(closure, 3),
            "chains": {
                "dialogue": {"score": chain_a.score, "gaps": chain_a.gaps},
                "state": {"score": chain_b.score, "gaps": chain_b.gaps},
                "trajectory": {"score": chain_c.score, "gaps": chain_c.gaps},
            },
            "weighted_score": round(
                chain_a.score * self.dialogue_coherence_weight +
                chain_b.score * self.state_consistency_weight +
                chain_c.score * self.emotion_continuity_weight,
                3,
            ),
            "weakest_chain": min(
                [("dialogue", chain_a.score), ("state", chain_b.score),
                 ("trajectory", chain_c.score)],
                key=lambda x: x[1],
            )[0],
        }

    def _eval_dialogue_coherence(self, response: dict,
                                 history: list[dict]) -> EvidenceChainResult:
        """Chain A: 对话连贯性——回应是否与最近的对话相关？"""
        if not history:
            return EvidenceChainResult("dialogue", 3.0, ["无对话历史"])

        resp_text = response.get("text", "")
        if not resp_text:
            return EvidenceChainResult("dialogue", 1.0, ["空回应"])

        # 检查回应是否与最近一轮对话的主题相关
        last_turn = history[-1] if history else {}
        last_text = last_turn.get("text", last_turn.get("content", ""))
        last_speaker = last_turn.get("speaker", last_turn.get("from", ""))

        score = 3.0
        gaps = []

        # 主题关联检测（简化版：关键词重叠）
        resp_words = set(resp_text)
        if last_text:
            last_words = set(last_text)
            overlap = len(resp_words & last_words)
            if overlap == 0:
                score -= 1.5
                gaps.append("回应与前一轮对话无词汇重叠")
            elif overlap < 3:
                score -= 0.5

        # 回应长度检查
        if len(resp_text) < 2:
            score -= 1.0
            gaps.append("回应过短")

        # 情绪匹配检查
        resp_emotion = response.get("emotion", "")
        if resp_emotion and "neutral" not in resp_emotion.lower():
            score += 0.5  # 有明确情绪是好的

        return EvidenceChainResult("dialogue", max(1.0, min(5.0, score)), gaps)

    def _eval_state_consistency(self, response: dict,
                                state_before: dict | None,
                                state_after: dict | None) -> EvidenceChainResult:
        """Chain B: 状态一致性——情感变更是否与回应一致？"""
        score = 3.0
        gaps = []

        if state_before is None or state_after is None:
            return EvidenceChainResult("state", 3.0, ["缺少状态快照"])

        # 检查 PAD 值是否在合理范围内变化
        before_pad = state_before.get("pad", {})
        after_pad = state_after.get("pad", {})
        if before_pad and after_pad:
            p_change = abs(after_pad.get("pleasure", 0) - before_pad.get("pleasure", 0))
            a_change = abs(after_pad.get("arousal", 0) - before_pad.get("arousal", 0))
            if p_change > 0.5:
                score -= 1.0
                gaps.append(f"愉悦度变化过大 (delta={p_change:.2f})")
            if a_change > 0.6:
                score -= 1.0
                gaps.append(f"唤醒度变化过大 (delta={a_change:.2f})")

        # 检查主导情感是否与回应的 emotional_expression 一致
        resp_emotion = response.get("emotion", response.get("emotional_expression", ""))
        dominant = state_after.get("dominant_emotion", "")
        if resp_emotion and dominant and resp_emotion != dominant:
            # 不完全一致不一定差——可能是有意识的表达控制
            score -= 0.5

        return EvidenceChainResult("state", max(1.0, min(5.0, score)), gaps)

    def _eval_emotion_trajectory(self,
                                 emotion_history: list[dict]) -> EvidenceChainResult:
        """Chain C: 情感轨迹连贯性——情绪是否平滑过渡而非跳变？"""
        if len(emotion_history) < 2:
            return EvidenceChainResult("trajectory", 3.0, ["情感历史不足"])

        score = 3.0
        gaps = []
        window = emotion_history[-self.trajectory_window:]

        # 计算相邻情感的 PAD 距离
        for i in range(1, len(window)):
            prev_pad = window[i-1].get("pad", {})
            curr_pad = window[i].get("pad", {})
            if prev_pad and curr_pad:
                distance = math.sqrt(
                    (curr_pad.get("pleasure", 0) - prev_pad.get("pleasure", 0))**2 +
                    (curr_pad.get("arousal", 0) - prev_pad.get("arousal", 0))**2
                )
                if distance > 0.4:
                    score -= 0.5
                    gaps.append(f"情感跳变 (dist={distance:.2f})")

        # 检查是否有单调模式（一直下降不健康）
        if len(window) >= 3:
            pleasures = [e.get("pad", {}).get("pleasure", 0) for e in window]
            if all(pleasures[i] > pleasures[i+1] for i in range(len(pleasures)-1)):
                score -= 0.5
                gaps.append("愉悦度持续下降")

        return EvidenceChainResult("trajectory", max(1.0, min(5.0, score)), gaps)


def _geometric_mean(scores: list[float]) -> float:
    """几何平均——弱链放大效应。"""
    if not scores or any(s <= 0 for s in scores):
        return 0.0
    return math.exp(sum(math.log(s) for s in scores) / len(scores))
