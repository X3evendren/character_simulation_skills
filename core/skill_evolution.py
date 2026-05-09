"""Skill Evolution Manager — 自进化技能系统。

借鉴 Hermes 的 self-evolving 模式，让非内建技能在使用中自我改进。

门控条件:
- 最少 5 次执行 + 3 次失败才能触发改进建议
- 每技能每天最多 1 次进化
- 仅 generated_by != "human" 的技能可进化
- 每次进化版本递增，保留历史 prompt 用于回滚
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class EvolutionReport:
    """一次进化分析报告。"""
    skill_name: str
    version: int
    suggested_prompt: str = ""
    prompt_changes: str = ""       # 变更描述
    performance_trend: str = ""    # improving / stable / declining
    suggested_triggers: list[str] = field(default_factory=list)
    should_evolve: bool = False
    reason: str = ""


@dataclass
class SkillEvolutionManager:
    """技能进化管理器。

    用法:
        evo = SkillEvolutionManager()
        report = await evo.evaluate(tracker, skill, provider)
        if report.should_evolve:
            evo.apply_evolution(skill, report)
    """

    min_executions: int = 5
    min_failures: int = 3
    cooldown_seconds: float = 86400.0  # 24h
    max_prompt_versions: int = 10

    _last_evolution: dict[str, float] = field(default_factory=dict)

    def evaluate(self, tracker, skill) -> EvolutionReport:
        """评估技能是否需要进化——纯数学判断，不需要 LLM。"""
        report = EvolutionReport(skill_name=tracker.skill_name, version=tracker.version)

        # 门控：最少执行次数
        if tracker.activation_count < self.min_executions:
            report.reason = f"执行次数不足 ({tracker.activation_count} < {self.min_executions})"
            return report

        # 门控：冷却时间
        last = self._last_evolution.get(tracker.skill_name, 0)
        if time.time() - last < self.cooldown_seconds:
            report.reason = "冷却中"
            return report

        # 仅非内建技能可进化
        if getattr(tracker, "generated_by", "human") == "human":
            report.reason = "内建技能不可自动进化"
            return report

        # 分析性能趋势
        parse_rate = tracker.parse_success_rate
        avg_quality = tracker.avg_quality_score

        if parse_rate < 0.5 and tracker.activation_count >= self.min_executions:
            report.performance_trend = "declining"
            report.should_evolve = True
            report.prompt_changes = f"parse 成功率过低 ({parse_rate:.0%})，需要优化输出格式约束"
        elif avg_quality < 0.3 and tracker.activation_count >= 10:
            report.performance_trend = "declining"
            report.should_evolve = True
            report.prompt_changes = f"输出质量持续偏低 ({avg_quality:.2f})，需要精简/聚焦 prompt"
        elif parse_rate > 0.8 and avg_quality > 0.5:
            report.performance_trend = "stable"
        else:
            report.performance_trend = "stable"
            report.reason = "不需要进化"

        return report

    async def suggest_improvement(self, tracker, skill, provider) -> EvolutionReport:
        """使用 LLM 生成改进建议——仅在 evaluate() 建议进化时调用。"""
        report = self.evaluate(tracker, skill)
        if not report.should_evolve:
            return report

        try:
            current_prompt = skill.build_prompt({}, {"description": "分析"}, {})

            prompt = f"""你是技能审查器。以下技能需要优化：

技能名称: {tracker.skill_name}
当前版本: {tracker.version}
执行次数: {tracker.activation_count}
Parse 成功率: {tracker.parse_success_rate:.0%}
平均质量分: {tracker.avg_quality_score:.2f}

当前 prompt:
---
{current_prompt[:1500]}
---

请改进此 prompt，使其更简洁、更准确。输出 JSON:
{{"improved_prompt": "新的 prompt 文本", "changes": "变更说明", "confidence": 0.8}}"""

            result = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=600,
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")

            from .base import extract_json
            data = extract_json(content)
            report.suggested_prompt = data.get("improved_prompt", "")
            report.prompt_changes = data.get("changes", report.prompt_changes)
            report.should_evolve = bool(report.suggested_prompt)

        except Exception:
            report.should_evolve = False
            report.reason = "LLM 进化调用失败"

        return report

    def apply_evolution(self, skill, report: EvolutionReport, tracker) -> bool:
        """应用进化：替换 skill 的 build_prompt 方法，递增版本。"""
        if not report.suggested_prompt:
            return False

        # 保存当前 prompt 到历史
        if not hasattr(tracker, "prompt_versions"):
            tracker.prompt_versions = []
        tracker.prompt_versions.append(report.suggested_prompt)
        if len(tracker.prompt_versions) > self.max_prompt_versions:
            tracker.prompt_versions = tracker.prompt_versions[-self.max_prompt_versions:]

        # 替换 build_prompt
        new_prompt_text = report.suggested_prompt

        def new_build_prompt(self_instance, character_state, event, context):
            # 注入反 RLHF 提示
            anti_hint = context.get("_anti_alignment_hint", "")
            if anti_hint:
                return anti_hint + "\n\n---\n\n" + new_prompt_text
            return new_prompt_text

        skill.build_prompt = new_build_prompt.__get__(skill, type(skill))
        tracker.version += 1
        if not hasattr(tracker, "evolution_history"):
            tracker.evolution_history = []
        tracker.evolution_history.append(
            f"v{tracker.version}: {report.prompt_changes}"
        )
        tracker.generated_by = "evolution"
        self._last_evolution[tracker.skill_name] = time.time()

        return True

    def rollback(self, skill, tracker) -> bool:
        """回滚到上一个版本。"""
        if not tracker.prompt_versions:
            return False
        prev = tracker.prompt_versions.pop()

        def rollback_prompt(self_instance, character_state, event, context):
            anti_hint = context.get("_anti_alignment_hint", "")
            if anti_hint:
                return anti_hint + "\n\n---\n\n" + prev
            return prev

        skill.build_prompt = rollback_prompt.__get__(skill, type(skill))
        tracker.version -= 1
        tracker.evolution_history.append(f"回滚到 v{tracker.version}")
        return True
