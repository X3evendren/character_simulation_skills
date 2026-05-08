"""OpenClaw-style boundary for channels, actions, and world feedback."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class WorldAdapter:
    events: list[dict] = field(default_factory=list)
    feedback_events: list[dict] = field(default_factory=list)

    def receive(self, channel: str, source: str, content: str, intensity: float = 0.5) -> dict:
        modality = "dialogue" if channel in ("chat", "dm", "email") else "text"
        event = {
            "t": time.time(),
            "channel": channel,
            "modality": modality,
            "source": source,
            "content": content,
            "intensity": max(0.0, min(1.0, intensity)),
        }
        self.events.append(event)
        return event

    def feedback(self, action: dict, result: str, valence: float = 0.0) -> dict:
        event = {
            "t": time.time(),
            "kind": "action_feedback",
            "action": dict(action),
            "result": result,
            "valence": max(-1.0, min(1.0, valence)),
        }
        self.feedback_events.append(event)
        return event

    def recent_feedback(self, n: int = 5) -> list[dict]:
        return list(self.feedback_events[-n:])
