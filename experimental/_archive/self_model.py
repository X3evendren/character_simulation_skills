"""Self Model — 维护第一人称自我/他人/冲突/面具/意图状态。

基于工作空间内容更新角色的自我模型，追踪未解决的内心冲突、
当前使用的社交面具、以及私下意图。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SelfModel:
    current_self_image: str = "我需要维持自己的体面。"
    current_other_model: str = "对方的意图尚不明确。"
    unresolved_conflict: str = ""
    active_mask: str = ""
    private_intention: str = ""
    history: list[dict] = field(default_factory=list)

    def update(self, workspace: list[dict]) -> dict:
        text = " ".join(str(item.get("content", "")) for item in workspace)
        kinds = {item.get("kind") for item in workspace}

        text_lower = text.lower()
        if any(w in text for w in ("fear", "afraid", "anxious", "没有回复", "抛", "离开", "abandon", "ignore", "silent", "沉默")) or ("anxiety" in text_lower):
            self.unresolved_conflict = "想靠近确认，但怕被抛下或显得太需要。"
            self.active_mask = "装作无所谓，用短句保护自尊。"
            self.private_intention = "希望对方主动解释并确认关系仍然安全。"
            self.current_other_model = "对方可能正在远离我，也可能只是没有意识到我的不安。"
        elif any(w in text for w in ("anger", "angry", "rage", "愤", "怒", "hate", "恨")):
            self.unresolved_conflict = "想攻击对方，又想保留关系。"
            self.active_mask = "把受伤包装成冷淡或讽刺。"
            self.private_intention = "让对方承认自己造成了伤害。"
        elif "response" in kinds:
            self.private_intention = "把已经形成的回应说出口，同时隐藏更脆弱的动机。"

        state = self.to_dict()
        self.history.append(state)
        self.history = self.history[-10:]
        return state

    def format_for_context(self) -> str:
        return (
            f"【自我模型】自我形象:{self.current_self_image} "
            f"他人模型:{self.current_other_model} "
            f"未说出口的冲突:{self.unresolved_conflict} "
            f"面具:{self.active_mask} "
            f"私下意图:{self.private_intention}"
        )[:300]

    def to_dict(self) -> dict:
        return {
            "current_self_image": self.current_self_image,
            "current_other_model": self.current_other_model,
            "unresolved_conflict": self.unresolved_conflict,
            "active_mask": self.active_mask,
            "private_intention": self.private_intention,
        }
