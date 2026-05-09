"""Procedural Memory Store — 存储触发-预测-防御-回应模式。

从反复出现的心理模式中学习规则，当相似情境再次出现时检索规则。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ProceduralMemoryStore:
    rules: list[dict] = field(default_factory=list)
    max_rules: int = 50

    def learn_rule(
        self,
        trigger: str,
        prediction: str,
        defense: str,
        response_style: str,
        weight: float = 0.5,
    ) -> dict:
        rule = {
            "t": time.time(),
            "trigger": trigger,
            "prediction": prediction,
            "defense": defense,
            "response_style": response_style,
            "weight": max(0.0, min(1.0, weight)),
        }
        self.rules.append(rule)
        self.rules.sort(key=lambda item: (item["weight"], item["t"]), reverse=True)
        self.rules = self.rules[:self.max_rules]
        return rule

    def retrieve(self, text: str, n: int = 3) -> list[dict]:
        scored = []
        chars = set(text)
        for rule in self.rules:
            trigger_chars = set(rule["trigger"])
            overlap = len(chars & trigger_chars) / max(len(trigger_chars), 1)
            synonym_hit = (
                ("沉默" in rule["trigger"] and ("没回" in text or "不回复" in text or "不接" in text)) or
                ("批评" in rule["trigger"] and ("责备" in text or "骂" in text or "说" in text))
            )
            score = overlap + (0.5 if synonym_hit else 0.0) + rule["weight"] * 0.3
            if score >= 0.35:
                item = dict(rule)
                item["match_score"] = score
                scored.append(item)
        scored.sort(key=lambda item: item["match_score"], reverse=True)
        return scored[:n]

    def to_dict(self) -> dict:
        return {"rules": list(self.rules), "max_rules": self.max_rules}

    @classmethod
    def from_dict(cls, data: dict) -> "ProceduralMemoryStore":
        return cls(rules=list(data.get("rules", [])), max_rules=data.get("max_rules", 50))
