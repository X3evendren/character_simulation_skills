"""自我模型 — 完整自我叙事。

维护助手的自我认知故事——随经历持续演化。
不同于简单的模板填充，这是一个持续的、可成长的叙事。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class GrowthEvent:
    """一次成长事件——自我叙事的一个增量更新"""
    timestamp: float
    event_type: str     # insight / relationship_change / skill_gained / value_shift
    description: str
    significance: float  # 0-1, 对自我认知的影响程度


@dataclass
class SelfModel:
    """助手的自我认知模型——随经历演化。

    五个维度:
    - core_identity: "我是谁" (从 assistant.md 初始化)
    - current_chapter: "我此刻在做什么、感受什么"
    - growth_log: "我最近学到了什么、有什么变化"
    - relationship_model: "我对这个用户的了解"
    - unresolved: "我还在思考但尚未有答案的事"
    """

    core_identity: str = ""
    current_chapter: str = "刚刚醒来，开始新的一天"
    growth_log: list[GrowthEvent] = field(default_factory=list)
    relationship_notes: dict[str, str] = field(default_factory=dict)  # topic → notes
    unresolved: list[str] = field(default_factory=list)
    last_reflection: float = 0.0
    reflection_interval: float = 30.0  # 自省间隔(秒)

    def init_from_config(self, config: dict):
        """从 assistant.md 配置初始化核心身份。"""
        name = config.get("name", "助手")
        essence = config.get("essence", "")
        traits = config.get("traits", "")
        self.core_identity = f"我是{name}。{essence} {traits}".strip()
        self.current_chapter = f"作为{name}，我准备好帮助用户。我保持温和但有边界——不迎合，不审判。"

    def should_reflect(self) -> bool:
        """是否应该触发周期性自省。"""
        return time.time() - self.last_reflection > self.reflection_interval

    def record_growth(self, event_type: str, description: str, significance: float = 0.5):
        """记录一次成长。"""
        self.growth_log.append(GrowthEvent(
            timestamp=time.time(),
            event_type=event_type,
            description=description,
            significance=significance,
        ))
        if len(self.growth_log) > 100:
            self.growth_log = self.growth_log[-100:]

    def update_relationship(self, topic: str, note: str):
        """更新对用户的了解。"""
        self.relationship_notes[topic] = note

    def add_unresolved(self, question: str):
        """添加一个未解问题。"""
        if question not in self.unresolved:
            self.unresolved.append(question)
        if len(self.unresolved) > 10:
            self.unresolved = self.unresolved[-10:]

    def resolve_question(self, question: str):
        """标记一个未解问题为已解答。"""
        if question in self.unresolved:
            self.unresolved.remove(question)

    def format_for_prompt(self) -> str:
        """格式化为可注入 Prompt 的自我认知摘要。"""
        parts = [f"【自我认知】{self.core_identity}"]
        parts.append(f"当前: {self.current_chapter}")
        if self.unresolved:
            parts.append(f"未解问题: {'; '.join(self.unresolved[-3:])}")
        if self.growth_log:
            recent = self.growth_log[-3:]
            parts.append("近期成长: " + "; ".join(g.description[:60] for g in recent))
        return "\n".join(parts)

    async def reflect(
        self,
        provider,
        recent_interactions: list[str],
        mindstate,
        drive_state,
    ) -> str:
        """低频 LLM 自省——更新自我叙事。

        用心理引擎的小模型执行，额外 Token 可控(~200 tokens)。
        返回更新后的 current_chapter。
        """
        self.last_reflection = time.time()

        prompt = f"""{self.core_identity}

回顾最近的交互:
{chr(10).join(f"- {r}" for r in recent_interactions[-5:])}

请用一句话更新你的当前状态描述。你在做什么？感受如何？学到了什么？
只输出一句话，不要解释。"""

        try:
            response = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.5, max_tokens=100,
            )
            new_chapter = response.content.strip()[:200]
            if new_chapter:
                self.current_chapter = new_chapter
            return new_chapter
        except Exception:
            return self.current_chapter

    def to_dict(self) -> dict:
        return {
            "core_identity": self.core_identity,
            "current_chapter": self.current_chapter,
            "growth_events": [{"type": g.event_type, "desc": g.description,
                              "sig": g.significance, "ts": g.timestamp}
                             for g in self.growth_log[-20:]],
            "relationship_notes": self.relationship_notes,
            "unresolved": self.unresolved,
        }
