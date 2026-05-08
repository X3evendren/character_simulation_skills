"""Skill Curator — 技能自动审查和自改进 (Hermes 模式)

借鉴 Hermes 的 curator.py: 用辅助 LLM 定期审查 Agent 创建的技能,
检测质量退化、冗余和过期内容。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CuratorReview:
    """一次 curator 审查的结果。"""
    skill_name: str
    reviewed_at: float
    health: str = "healthy"  # healthy / degraded / redundant / should_archive
    suggestions: list[str] = field(default_factory=list)
    quality_score: float = 0.5


@dataclass
class SkillCurator:
    """技能审查器。

    审查策略:
    - 每 7 天审查一次 Agent 创建的技能
    - 审查标准: 激活频率、输出质量、与同类 skills 的重叠度
    - 产出: health report + suggestions
    """

    review_interval_days: int = 7
    reviews: dict[str, list[CuratorReview]] = field(default_factory=dict)
    _last_review_time: float = 0.0

    def should_review(self) -> bool:
        """是否应该触发审查?"""
        return (time.time() - self._last_review_time) > self.review_interval_days * 86400

    def review(self, skill_name: str, tracker) -> CuratorReview:
        """审查单个技能。纯数学判断, 不需要 LLM。"""
        health = "healthy"
        suggestions = []

        # 激活频率检查
        if tracker.days_since_activation() > 30:
            health = "degraded"
            suggestions.append("长期未激活, 考虑归档")

        # 质量检查
        if tracker.avg_quality_score < 0.3 and tracker.activation_count > 5:
            if health == "healthy":
                health = "degraded"
            suggestions.append("输出质量持续偏低, 需要优化 prompt")

        # 冗余检查
        for other, overlap in tracker.output_overlap_with.items():
            if overlap > 0.7:
                health = "redundant"
                suggestions.append(f"与 {other} 高度重叠({overlap:.0%}), 建议合并")

        # 过度消耗检查
        if tracker.avg_token_cost > 0 and tracker.activation_count > 10:
            if tracker.avg_token_cost > 800:
                suggestions.append(f"Token 消耗过高({tracker.avg_token_cost:.0f}/call), 考虑精简 prompt")

        review = CuratorReview(
            skill_name=skill_name,
            reviewed_at=time.time(),
            health=health,
            suggestions=suggestions,
            quality_score=tracker.avg_quality_score,
        )

        self.reviews.setdefault(skill_name, []).append(review)
        return review

    async def review_with_llm(self, skill_name: str, skill_content: str,
                              provider, quality_score: float) -> CuratorReview:
        """使用辅助 LLM 做深度审查 (可选)。"""
        prompt = f"""你是技能审查器。审查以下 Agent 创建的技能, 决定是否健康。

技能名称: {skill_name}
激活数据: 质量分 {quality_score:.2f}

技能内容:
{skill_content[:2000]}

评估:
1. 这个技能是否仍然有用?
2. prompt 是否清晰完整?
3. 输出格式是否合理?
4. 有没有可以改进的地方?

输出 JSON:
{{"health": "healthy/degraded/redundant/should_archive",
  "suggestions": ["建议1", "建议2"],
  "quality_score": 0.5}}"""

        try:
            result = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.2, max_tokens=300,
            )
            content = result["choices"][0]["message"]["content"].strip()
            from character_mind.core.base import extract_json
            data = extract_json(content)
            review = CuratorReview(
                skill_name=skill_name,
                reviewed_at=time.time(),
                health=data.get("health", "healthy"),
                suggestions=data.get("suggestions", []),
                quality_score=data.get("quality_score", quality_score),
            )
            self.reviews.setdefault(skill_name, []).append(review)
            return review
        except Exception:
            # LLM 失败: 使用数学审查
            from character_mind.experimental.skill_metabolism import SkillTracker
            tracker = SkillTracker(skill_name=skill_name, layer=0)
            tracker.avg_quality_score = quality_score
            return self.review(skill_name, tracker)

    def get_health_report(self) -> dict:
        """生成所有技能的审查报告。"""
        healthy = degraded = redundant = 0
        for skill_reviews in self.reviews.values():
            if not skill_reviews:
                continue
            latest = skill_reviews[-1]
            if latest.health == "healthy":
                healthy += 1
            elif latest.health == "degraded":
                degraded += 1
            else:
                redundant += 1
        return {"healthy": healthy, "degraded": degraded, "redundant": redundant,
                "total_reviewed": healthy + degraded + redundant}

    def to_dict(self) -> dict:
        return {
            "reviews": {
                k: [{"skill_name": r.skill_name, "reviewed_at": r.reviewed_at,
                     "health": r.health, "suggestions": r.suggestions}
                    for r in v]
                for k, v in self.reviews.items()
            }
        }
