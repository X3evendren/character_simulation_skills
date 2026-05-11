"""反馈闭环 — 抄 DBNT (Do Better Next Time) + Dual-Process Agent。

结构化反馈协议: 三级反馈收集 + 隐式推断 + 对话中自然收集。
成功信号高权重 (1.5×)。FSRS-6 衰减引擎。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class FeedbackLevel(str, Enum):
    """反馈级别 — 抄 DBNT 的 escalating correction"""
    GENTLE = "gentle"       # 微调建议——下次注意即可
    NORMAL = "normal"       # 明确纠正——应该改进
    CRITICAL = "critical"   # 严重错误——必须记录为规则


@dataclass
class FeedbackEvent:
    """一次反馈事件"""
    timestamp: float
    level: FeedbackLevel
    source: str             # "explicit" / "implicit" / "auto"
    context: str            # 当时的对话上下文
    description: str        # 反馈描述
    pattern: str = ""       # 提取的模式（供自动提升）
    applied: bool = False   # 是否已应用为规则


@dataclass
class FeedbackRule:
    """一条持久化的反馈规则"""
    rule_id: str
    content: str                    # 规则内容
    pattern: str                    # 触发模式
    level: FeedbackLevel
    created_at: float
    last_applied: float = 0.0
    apply_count: int = 0
    success_count: int = 0          # 规则应用后成功的次数
    stability: float = 0.0          # FSRS-6 稳定性评分
    difficulty: float = 0.3         # FSRS-6 难度评分

    @property
    def is_permanent(self) -> bool:
        """连续 3 次应用成功 → 提升为永久规则"""
        return self.apply_count >= 3 and self.success_rate > 0.66

    @property
    def success_rate(self) -> float:
        if self.apply_count == 0:
            return 0.5
        return self.success_count / self.apply_count


class FeedbackLoop:
    """反馈闭环 — 抄 DBNT + Dual-Process Agent。

    三个反馈来源:
    1. 显式命令: /good /bad /remember
    2. 隐式推断: 用户重复提问 = 不好; 用户说"谢谢" = 好
    3. 自动收集: 心理学引擎在每次回应时评估 quality
    """

    def __init__(self):
        self._events: list[FeedbackEvent] = []
        self._rules: dict[str, FeedbackRule] = {}
        self._rule_counter: int = 0
        self._pattern_buffer: dict[str, int] = {}  # pattern → 出现次数

    # ═══ 收集 ═══

    def record_explicit(self, level: FeedbackLevel, context: str, description: str):
        """显式命令反馈: /good /bad /remember"""
        event = FeedbackEvent(
            timestamp=time.time(),
            level=level,
            source="explicit",
            context=context,
            description=description,
        )
        self._events.append(event)
        self._check_pattern(event)

    def infer_from_response(self, user_reply: str, context: str) -> FeedbackEvent | None:
        """隐式推断: 从用户后续行为推断满意度。

        - 用户重复同一个问题 → 上次回答不好 (NORMAL)
        - 用户说"谢谢" / "好的" / "明白了" → 正面 (GENTLE success)
        - 用户沉默 > 30 秒后重新输入 → 中性
        """
        event = None
        reply_lower = user_reply.lower()

        # 正面信号
        positive = ["谢谢", "好的", "明白了", "懂了", "有用", "对", "没错", "正是"]
        if any(w in reply_lower for w in positive):
            event = FeedbackEvent(
                timestamp=time.time(),
                level=FeedbackLevel.GENTLE,
                source="implicit",
                context=context,
                description="用户正面回应",
            )
            event.applied = True  # 正面反馈直接应用

        # 负面信号
        negative_patterns = ["不是", "不对", "你理解错了", "再试", "重来", "没听懂"]
        if any(w in reply_lower for w in negative_patterns):
            event = FeedbackEvent(
                timestamp=time.time(),
                level=FeedbackLevel.NORMAL,
                source="implicit",
                context=context,
                description="用户纠正或否定",
            )

        if event:
            self._events.append(event)
            self._check_pattern(event)
        return event

    def record_auto_quality(self, quality_score: float, context: str):
        """自动收集: 心理学引擎的 quality 评估。

        quality > 0.7 → 正面
        quality < 0.3 → 需要改进
        """
        if quality_score >= 0.7:
            level = FeedbackLevel.GENTLE
            desc = f"自动评估: 质量 {quality_score:.2f}"
        elif quality_score < 0.3:
            level = FeedbackLevel.NORMAL
            desc = f"自动评估: 低质量 {quality_score:.2f}"
        else:
            return  # 中等质量不记录

        event = FeedbackEvent(
            timestamp=time.time(),
            level=level,
            source="auto",
            context=context,
            description=desc,
        )
        self._events.append(event)
        self._check_pattern(event)

    # ═══ 模式识别 ═══

    def _check_pattern(self, event: FeedbackEvent):
        """检测重复模式——同类型反馈连续出现 → 自动提升为规则。"""
        if event.level in (FeedbackLevel.GENTLE,):
            return  # 轻微反馈不触发模式检测

        # 简化模式提取: 取 context 的前 60 字符作为模式签名
        pattern = event.context[:80].lower()
        self._pattern_buffer[pattern] = self._pattern_buffer.get(pattern, 0) + 1

        if self._pattern_buffer[pattern] >= 3:
            # 触发自动提升
            self._promote_to_rule(pattern, event)

    def _promote_to_rule(self, pattern: str, event: FeedbackEvent):
        """自动提升为持久规则。

        抄 DBNT: 连续 3 次相同失败模式 → 永久规则。
        """
        self._rule_counter += 1
        rule = FeedbackRule(
            rule_id=f"rule_{self._rule_counter}",
            content=f"避免重复: {event.description}",
            pattern=pattern,
            level=event.level,
            created_at=time.time(),
        )
        self._rules[rule.rule_id] = rule
        self._pattern_buffer[pattern] = 0  # 重置计数器

    # ═══ 查询 ═══

    def get_active_rules(self, context: str) -> list[FeedbackRule]:
        """获取与当前情境相关的活跃规则。

        FSRS-6 衰减: 规则用到的强化 (stability↑), 不用的淡化 (stability↓)。
        """
        context_lower = context.lower()
        relevant = []

        for rule in self._rules.values():
            # 模式匹配
            if any(word in context_lower for word in rule.pattern.split()):
                # FSRS-6: 每次匹配时更新
                if rule.last_applied > 0:
                    days_since = (time.time() - rule.last_applied) / 86400
                    # 不用的规则稳定性衰减
                    rule.stability *= max(0.1, 1.0 - days_since * 0.1)

                rule.last_applied = time.time()
                rule.apply_count += 1
                # 成功的规则稳定性上升
                rule.stability = min(1.0, rule.stability + 0.1)
                relevant.append(rule)

        # 过滤: 永久规则 + 稳定性 > 0.3 的规则
        return [r for r in relevant if r.is_permanent or r.stability > 0.3]

    def record_rule_outcome(self, rule_id: str, success: bool):
        """记录一条规则应用后的结果。

        成功 → stability↑, 权重 1.5× (抄 DBNT)。
        失败 → stability↓。
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return
        if success:
            rule.success_count += 1
            rule.stability = min(1.0, rule.stability + 0.15)  # 1.5× 加权
        else:
            rule.stability = max(0.0, rule.stability - 0.1)

    def format_rules_for_prompt(self, rules: list[FeedbackRule]) -> str:
        """将反馈规则格式化为 Prompt 注入文本。"""
        if not rules:
            return ""
        lines = ["【从经验中学到的】"]
        for r in rules:
            tag = "[永久]" if r.is_permanent else f"[学习中:{r.stability:.1f}]"
            lines.append(f"- {tag} {r.content}")
        return "\n".join(lines)

    # ═══ 统计 ═══

    def stats(self) -> dict:
        total_events = len(self._events)
        total_rules = len(self._rules)
        permanent = sum(1 for r in self._rules.values() if r.is_permanent)
        return {
            "total_feedback_events": total_events,
            "total_rules": total_rules,
            "permanent_rules": permanent,
            "recent_events": [
                {"level": e.level.value, "source": e.source, "desc": e.description[:60]}
                for e in self._events[-5:]
            ],
        }
