"""会话级运行时工厂 — 每个会话拥有独立的 registry snapshot、记忆、对话、生物状态。"""
from __future__ import annotations

from dataclasses import dataclass

from .conversation_history import ConversationHistoryStore
from .episodic_memory import EpisodicMemoryStore
from .orchestrator import CognitiveOrchestrator
from .registry import SkillRegistry, build_registry_from_profile


@dataclass
class SessionRuntime:
    """会话级运行时容器。"""
    registry: SkillRegistry
    orchestrator: CognitiveOrchestrator
    episodic_store: EpisodicMemoryStore
    conversation_store: ConversationHistoryStore | None
    biological_bridge: object | None = None


def create_runtime(
    *,
    include_experimental: bool = False,
    anti_alignment_enabled: bool = True,
    episodic_store: EpisodicMemoryStore | None = None,
    conversation_store: ConversationHistoryStore | None = None,
    biological_bridge=None,
) -> SessionRuntime:
    """创建一个新的会话级运行时实例。"""
    registry = build_registry_from_profile(include_experimental=include_experimental)
    episodic = episodic_store or EpisodicMemoryStore()
    orchestrator = CognitiveOrchestrator(
        registry=registry,
        episodic_store=episodic,
        conversation_store=conversation_store,
        anti_alignment_enabled=anti_alignment_enabled,
        biological_bridge=biological_bridge,
    )
    return SessionRuntime(
        registry=registry,
        orchestrator=orchestrator,
        episodic_store=episodic,
        conversation_store=conversation_store,
        biological_bridge=biological_bridge,
    )
