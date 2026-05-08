"""NLA-inspired internal-state auditor.

This module verbalizes internal traces as hypotheses, not as ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExperienceAuditor:
    def verbalize(self, trace: dict) -> dict:
        inner = trace.get("inner_experience", {}).get("items", [])
        outer = trace.get("outer_behavior", {})
        emotions = [item.get("content", "") for item in inner if item.get("kind") == "felt_emotion"]
        private = [item.get("content", "") for item in inner if not item.get("expressible", True)]
        divergence = self.divergence_score(inner, outer)
        parts = []
        if emotions:
            parts.append(f"内部情绪线索: {', '.join(emotions[:3])}")
        if private:
            parts.append(f"存在未直接表达内容: {'; '.join(private[:2])}")
        if divergence > 0.5:
            parts.append("检测到内外不一致: 外部表达可能经过面具、压抑或策略过滤")
        return {
            "status": "假设性解释，不等同于主观体验证明",
            "divergence_score": divergence,
            "summary": "。".join(parts) if parts else "未检测到强内部线索",
        }

    def divergence_score(self, inner_items: list[dict], outer_behavior: dict) -> float:
        outer_text = outer_behavior.get("content", "")
        private_pressure = sum(
            item.get("intensity", 0.0)
            for item in inner_items
            if not item.get("expressible", True)
        )
        hidden_terms = [
            item.get("content", "")
            for item in inner_items
            if not item.get("expressible", True)
        ]
        direct_leak = any(term and term in outer_text for term in hidden_terms)
        score = min(1.0, private_pressure / 2.0)
        if direct_leak:
            score *= 0.4
        return score

    async def verbalize_llm(self, provider, trace: dict) -> dict:
        prompt = (
            "你是内部状态审计器。请把以下智能体内部状态轨迹解释为普通语言。"
            "必须声明这只是线索性假设，不是主观体验证明。\n\n"
            f"TRACE:\n{trace}"
        )
        result = await provider.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=180,
        )
        content = result["choices"][0]["message"]["content"].strip()
        return {
            "status": "假设性解释，不等同于主观体验证明",
            "summary": content[:500],
        }
