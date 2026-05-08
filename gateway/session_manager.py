"""Gateway Session Manager — 将 CharacterMind 实例与会话绑定。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from character_mind.core.session import SessionKey, Session, SessionManager


@dataclass
class GatewaySessionManager:
    """管理 Gateway 层的会话生命周期——每个会话对应一个 CharacterMind 实例。"""

    base_session_manager: SessionManager = field(default_factory=SessionManager)
    character_minds: dict[str, object] = field(default_factory=dict)
    idle_timeout: float = 3600.0  # 1 小时

    def get_or_create_mind(self, key: SessionKey, provider, character_profile: dict
                          ) -> object:
        """为会话获取或创建 CharacterMind 实例。"""
        sid = key.to_string()
        session = self.base_session_manager.get_or_create(key)

        if sid not in self.character_minds:
            from character_mind.core.runtime_v2 import CharacterMind
            mind = CharacterMind(provider, character_profile)
            mind.blackboard.write("session_id", sid)
            mind.blackboard.write("trust_level", key.trust_level.value)
            self.character_minds[sid] = mind

        session.touch()
        return self.character_minds[sid]

    def cleanup(self):
        """清理空闲会话。"""
        expired = []
        for sid, mind in self.character_minds.items():
            session = self.base_session_manager.get(sid)
            if session and session.idle_seconds() > self.idle_timeout:
                expired.append(sid)
        for sid in expired:
            self.character_minds.pop(sid, None)
            self.base_session_manager.remove(sid)
        return len(expired)

    def list_active(self) -> list[dict]:
        sessions = self.base_session_manager.list_active()
        for s in sessions:
            s["has_mind"] = s["session_id"] in self.character_minds
        return sessions
