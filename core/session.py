"""会话管理 — 闭环追踪 + 状态持久化。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .fsm import FiniteStateMachine, State, FSMContext
from .mind_state import MindState


@dataclass
class Session:
    """单个会话的状态容器。"""

    session_id: str
    fsm: FiniteStateMachine = field(default_factory=FiniteStateMachine)
    mindstate: MindState = field(default_factory=MindState)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    turn_count: int = 0
    total_tokens: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def touch(self):
        self.last_active = time.time()

    def record_turn(self, tokens: int = 0):
        self.turn_count += 1
        self.total_tokens += tokens
        self.touch()

    def record_error(self, error: str):
        self.errors.append(f"[turn {self.turn_count}] {error}")
        if len(self.errors) > 50:
            self.errors = self.errors[-50:]

    def stats(self) -> dict:
        return {
            "session_id": self.session_id,
            "fsm_state": self.fsm.state.value,
            "turn_count": self.turn_count,
            "total_tokens": self.total_tokens,
            "mindstate": self.mindstate.to_dict(),
            "errors": self.errors[-5:],
        }

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "fsm_state": self.fsm.state.value,
            "turn_count": self.turn_count,
            "total_tokens": self.total_tokens,
            "mindstate": self.mindstate.to_dict(),
            "created_at": self.created_at,
            "last_active": self.last_active,
            "metadata": self.metadata,
        }
