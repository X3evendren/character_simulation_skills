"""Private inner experience stream for phenomenological agents."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class InnerExperienceStream:
    max_items: int = 100
    items: list[dict] = field(default_factory=list)

    def append(
        self,
        kind: str,
        content: str,
        intensity: float,
        source: str,
        expressible: bool = True,
    ) -> dict:
        item = {
            "t": time.time(),
            "kind": kind,
            "content": content,
            "intensity": max(0.0, min(1.0, intensity)),
            "source": source,
            "expressible": expressible,
        }
        self.items.append(item)
        self.items = self.items[-self.max_items:]
        return item

    def recent(self, n: int = 10, *, include_private: bool = True) -> list[dict]:
        items = self.items if include_private else [
            item for item in self.items if item.get("expressible", True)
        ]
        return list(items[-n:])

    def format_for_context(self, include_private: bool = False, n: int = 8) -> str:
        recent = self.recent(n, include_private=include_private)
        if not recent:
            return "【内部流】无显著内部内容"
        lines = ["【内部流】"]
        for item in recent:
            privacy = "可表达" if item.get("expressible", True) else "不可直接表达"
            lines.append(
                f"- {item['kind']}({item['intensity']:.2f},{privacy}): {item['content']}"
            )
        return "\n".join(lines)

    def record_divergence(self, inner: dict, outer: dict, mechanism: str) -> dict:
        record = {
            "t": time.time(),
            "kind": "inner_outer_divergence",
            "inner": dict(inner),
            "outer": dict(outer),
            "mechanism": mechanism,
            "intensity": inner.get("intensity", 0.5),
            "source": "expression_policy",
            "expressible": False,
        }
        self.items.append(record)
        self.items = self.items[-self.max_items:]
        return record

    def to_dict(self) -> dict:
        return {"max_items": self.max_items, "items": list(self.items)}

    @classmethod
    def from_dict(cls, data: dict) -> "InnerExperienceStream":
        return cls(
            max_items=data.get("max_items", 100),
            items=list(data.get("items", [])),
        )
