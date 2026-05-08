"""Session Manager — 会话管理 (借鉴 OpenClaw session 命名 + Hermes SessionSource)"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class TrustLevel(Enum):
    OWNER = "owner"       # 角色自身, main 会话
    APPROVED = "approved" # 已审批的 DM
    GUEST = "guest"       # 未审批的陌生人
    GROUP = "group"       # 群聊


@dataclass
class SessionKey:
    """会话标识符, 编码了"谁的会话"和"信任级别" (OpenClaw 模式)。

    agent:<name>:main            — 角色自身 (最高信任)
    agent:<name>:dm:<user_id>    — 私聊
    agent:<name>:group:<id>      — 群聊
    agent:<name>:cron:<job_id>   — 定时任务
    """
    agent_name: str
    key_type: str = "main"  # main / dm / group / cron
    identifier: str = ""

    @classmethod
    def main(cls, agent_name: str = "character") -> "SessionKey":
        return cls(agent_name, "main")

    @classmethod
    def dm(cls, agent_name: str, user_id: str) -> "SessionKey":
        return cls(agent_name, "dm", user_id)

    @classmethod
    def group(cls, agent_name: str, group_id: str) -> "SessionKey":
        return cls(agent_name, "group", group_id)

    @classmethod
    def cron(cls, agent_name: str, job_id: str) -> "SessionKey":
        return cls(agent_name, "cron", job_id)

    def to_string(self) -> str:
        base = f"agent:{self.agent_name}:{self.key_type}"
        if self.identifier:
            base += f":{self.identifier}"
        return base

    @classmethod
    def from_string(cls, s: str) -> "SessionKey":
        parts = s.split(":")
        if len(parts) >= 3 and parts[0] == "agent":
            return cls(
                agent_name=parts[1],
                key_type=parts[2],
                identifier=parts[3] if len(parts) > 3 else "",
            )
        return cls("unknown", "main")

    @property
    def trust_level(self) -> TrustLevel:
        if self.key_type == "main":
            return TrustLevel.OWNER
        elif self.key_type == "dm":
            return TrustLevel.APPROVED
        elif self.key_type == "group":
            return TrustLevel.GROUP
        return TrustLevel.GUEST

    @property
    def is_sandboxed(self) -> bool:
        return self.key_type in ("dm", "group")


@dataclass
class Session:
    """单个会话的状态。

    每个会话有独立的:
    - conversation_history (对话记录)
    - memory_snapshot (角色记忆状态)
    - context_assembly (系统提示缓存)
    """
    session_id: str
    session_key: SessionKey
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    message_count: int = 0
    is_active: bool = True

    # 会話历史 (已有 ConversationHistoryStore)
    history_length: int = 0

    # 记忆快照
    memory_snapshot: dict = field(default_factory=dict)

    def touch(self):
        self.last_active = time.time()
        self.message_count += 1

    def idle_seconds(self) -> float:
        return time.time() - self.last_active

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "session_key": self.session_key.to_string(),
            "trust_level": self.session_key.trust_level.value,
            "sandboxed": self.session_key.is_sandboxed,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "message_count": self.message_count,
            "idle_seconds": self.idle_seconds(),
        }


@dataclass
class SessionManager:
    """会话生命周期管理。"""

    agent_name: str = "character"
    max_sessions: int = 64
    idle_timeout: float = 3600.0  # 1 小时

    _sessions: dict[str, Session] = field(default_factory=dict)

    def get_or_create(self, key: SessionKey) -> Session:
        sid = key.to_string()
        if sid in self._sessions:
            session = self._sessions[sid]
            session.touch()
            return session

        session = Session(session_id=sid, session_key=key)
        self._sessions[sid] = session
        self._trim()
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def remove(self, session_id: str):
        self._sessions.pop(session_id, None)

    def _trim(self):
        """淘汰过期和超量会话。"""
        # 淘汰超时
        expired = [
            sid for sid, s in self._sessions.items()
            if s.idle_seconds() > self.idle_timeout
        ]
        for sid in expired:
            self._sessions.pop(sid)

        # 淘汰超量
        if len(self._sessions) > self.max_sessions:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda x: x[1].last_active,
            )
            for sid, _ in sorted_sessions[:len(self._sessions) - self.max_sessions]:
                self._sessions.pop(sid)

    def list_active(self) -> list[dict]:
        return [s.to_dict() for s in self._sessions.values() if s.is_active]

    def __len__(self) -> int:
        return len(self._sessions)
