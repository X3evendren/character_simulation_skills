"""自反思周期 — 抄 EvolveR + MetaClaw 的双过程适应。

快速 (每轮): 分析成败 → 更新工作记忆
慢速 (每会话): 反思整体 → 蒸馏可复用模式 → 更新技能库
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ReflectionEntry:
    """一次反思条目"""
    timestamp: float
    type: str           # "fast" / "slow"
    what_went_well: str
    what_went_wrong: str
    insight: str        # 可复用的洞察
    action_items: list[str] = field(default_factory=list)


class SelfReflection:
    """自反思引擎 — 抄 EvolveR 的闭环经验生命周期。

    快速反思: 每轮 LLM 交互后立即执行（纯模板，零 Token）
    慢速反思: 每会话结束或每 N 轮触发（LLM 深度反思）
    """

    def __init__(self, fast_interval: int = 1, slow_interval: int = 20):
        self.fast_interval = fast_interval
        self.slow_interval = slow_interval
        self._entries: list[ReflectionEntry] = []
        self._turn_buffer: list[dict] = []  # 最近的交互缓冲
        self._last_slow_reflection: float = 0.0

    # ═══ 快速反思 (每轮) ═══

    def fast_reflect(
        self,
        user_input: str,
        assistant_response: str,
        psychology_result=None,
    ) -> ReflectionEntry:
        """快速反思 — 纯模板，零 Token。

        分析这一轮的基本成败信号:
        - 回应是否太短/太长？
        - 有没有明显的错误？
        - 心理学引擎的情感是否合适？
        """
        what_well = ""
        what_wrong = ""

        # 长度检查
        if len(assistant_response) < 10:
            what_wrong = "回应太短，可能不够完整"
        elif len(assistant_response) > 500:
            what_wrong = "回应太长，应该更简洁"

        # 心理学结果检查
        if psychology_result:
            emo = getattr(psychology_result, 'emotion', None)
            if emo and emo.intensity > 0.8:
                what_well = f"情感强度高 ({emo.dominant})，回应有情感温度"

        entry = ReflectionEntry(
            timestamp=time.time(),
            type="fast",
            what_went_well=what_well or "正常回应",
            what_went_wrong=what_wrong or "无明显问题",
            insight="",
        )
        self._entries.append(entry)
        self._turn_buffer.append({
            "user": user_input[:200],
            "assistant": assistant_response[:200],
            "well": what_well,
            "wrong": what_wrong,
        })

        if len(self._entries) > 200:
            self._entries = self._entries[-200:]
        if len(self._turn_buffer) > 50:
            self._turn_buffer = self._turn_buffer[-50:]

        return entry

    # ═══ 慢速反思 (每 N 轮) ═══

    def should_slow_reflect(self, turn_count: int) -> bool:
        """是否触发慢速反思。"""
        return (turn_count % self.slow_interval == 0 and turn_count > 0)

    def should_session_reflect(self) -> bool:
        """会话是否结束（触发最终慢速反思）。"""
        return len(self._turn_buffer) > 0

    async def slow_reflect(
        self,
        provider,
        self_model,          # SelfModel 实例
        skill_library,       # SkillLibrary 实例
    ) -> list[str]:
        """慢速反思 — LLM 深度分析最近的交互。

        1. 回顾最近 20 轮
        2. 识别重复失败模式
        3. 提炼可复用洞察
        4. 尝试演化技能库
        5. 更新自我叙事
        """
        if not self._turn_buffer:
            return []

        recent = self._turn_buffer[-20:]
        summary_lines = []
        for i, t in enumerate(recent):
            summary_lines.append(
                f"{i+1}. 用户: {t['user'][:60]}\n"
                f"   助手: {t['assistant'][:60]}\n"
                f"   {'✓' if not t['wrong'] or t['wrong'] == '无明显问题' else '✗'} "
                f"{t.get('well', '')} {t.get('wrong', '')}"
            )
        summary = "\n".join(summary_lines)

        prompt = f"""回顾以下最近的交互。识别重复的失败模式，提炼可复用的洞察。

{summary}

请输出:
1. 重复的问题模式（如果有）
2. 可以改进的地方
3. 一条你学到的东西（用于更新自我认知）

用简洁的要点输出。"""

        try:
            resp = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=400,
            )
            analysis = resp.content.strip()

            # 提取洞察
            insights = [line.strip("- ") for line in analysis.split("\n")
                       if line.strip().startswith("-") or line.strip().startswith("1.")]

            entry = ReflectionEntry(
                timestamp=time.time(),
                type="slow",
                what_went_well="",
                what_went_wrong="",
                insight=analysis[:500],
                action_items=insights[:5],
            )
            self._entries.append(entry)
            self._last_slow_reflection = time.time()

            # 尝试从失败模式演化技能
            failure_patterns = [t for t in recent if t.get('wrong') and t['wrong'] != '无明显问题']
            if len(failure_patterns) >= 3:
                failure_desc = "; ".join(t['wrong'] for t in failure_patterns[:5])
                context = "; ".join(t['user'][:50] for t in failure_patterns[:5])
                await skill_library.evolve(
                    failure_context=context,
                    failure_description=failure_desc,
                    provider=provider,
                )

            # 更新自我叙事
            if insights and self_model:
                insight_text = insights[0] if insights else ""
                if insight_text:
                    self_model.record_growth(
                        "reflection",
                        f"经过 {len(recent)} 轮交互的反思: {insight_text}",
                        significance=0.6,
                    )

            return insights
        except Exception:
            return []

    def get_recent_insights(self, n: int = 5) -> list[str]:
        """获取最近的反思洞察。"""
        slow_entries = [e for e in self._entries if e.type == "slow"]
        insights = []
        for e in slow_entries[-n:]:
            if e.insight:
                insights.append(e.insight[:200])
        return insights

    def stats(self) -> dict:
        return {
            "total_reflections": len(self._entries),
            "fast_count": sum(1 for e in self._entries if e.type == "fast"),
            "slow_count": sum(1 for e in self._entries if e.type == "slow"),
            "recent_insights": self.get_recent_insights(3),
        }
