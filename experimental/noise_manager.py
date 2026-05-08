"""Noise Manager — 上下文噪音查询和自动清理。

噪音 = 对当前体验无贡献但仍占据上下文的内容。
Agent 可被询问"当前上下文噪音占比如何", 根据反馈优化。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NoiseManager:
    """聚合噪音率的统一查询接口。"""

    memory_metabolism: object | None = None   # MemoryMetabolism
    skill_metabolism: object | None = None    # SkillMetabolism
    auto_clean_threshold: float = 0.5        # 噪音率超过此值触发自动清理

    def total_noise_ratio(self) -> float:
        """综合噪音率: 记忆噪音 + Skills 噪音的加权平均。"""
        mem_ratio = 0.0
        skill_ratio = 0.0
        mem_weight = 0.0
        skill_weight = 0.0

        if self.memory_metabolism is not None:
            mem_ratio = self.memory_metabolism.noise_ratio()
            mem_weight = 0.6

        if self.skill_metabolism is not None:
            report = self.skill_metabolism.get_noise_report()
            skill_ratio = report.get("skill_noise_ratio", 0.0)
            skill_weight = 0.4

        total_weight = mem_weight + skill_weight
        if total_weight == 0:
            return 0.0
        return (mem_ratio * mem_weight + skill_ratio * skill_weight) / total_weight

    def should_clean(self) -> bool:
        return self.total_noise_ratio() > self.auto_clean_threshold

    def report(self) -> dict:
        """生成完整噪音报告。"""
        mem_report = {}
        skill_report = {}
        if self.memory_metabolism is not None:
            mem_report = self.memory_metabolism.noise_report()
        if self.skill_metabolism is not None:
            skill_report = self.skill_metabolism.get_noise_report()

        return {
            "total_noise_ratio": round(self.total_noise_ratio(), 2),
            "auto_clean_triggered": self.should_clean(),
            "memory": mem_report,
            "skills": skill_report,
        }

    def format_for_agent(self) -> str:
        """格式化为可供 Agent 阅读的文本。"""
        r = self.report()
        lines = [f"【噪音报告】综合噪音率: {r['total_noise_ratio']:.0%}"]
        mem = r.get("memory", {})
        if mem:
            lines.append(f"记忆: {mem.get('total_memories',0)}条 "
                        f"(W:{mem.get('working_count',0)} S:{mem.get('short_count',0)} "
                        f"L:{mem.get('long_count',0)} C:{mem.get('core_count',0)} "
                        f"A:{mem.get('archive_count',0)}) "
                        f"噪音率: {mem.get('noise_ratio',0):.0%}")
        skills = r.get("skills", {})
        if skills:
            lines.append(f"Skills: {skills.get('total_skills',0)}个 "
                        f"(flagged:{skills.get('flagged',0)} merge:{skills.get('merge_candidates',0)} "
                        f"optimize:{skills.get('optimize_candidates',0)})")
        if r["auto_clean_triggered"]:
            lines.append("⚠ 噪音超过阈值, 建议触发自动清理。")
        return "\n".join(lines)
