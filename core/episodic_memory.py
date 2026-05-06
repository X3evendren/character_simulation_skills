"""事件记忆 — Episodic Memory with Emotional Tagging

基于 AdaMem (2026) 和 MENTOR (2026):
- 存储关键事件及其情感签名
- 按时间、情感相似度、语义标签检索
- 提供 character_state 的 "long-term memory" 层

设计:
- 内存存储（后续可替换为向量数据库）
- 每个事件记忆包含: timestamp, description, emotional_signature, significance, tags
- 检索支持: 最近的N个事件 + 情感相似事件 + 标签过滤
"""
from __future__ import annotations

import time
import math
from dataclasses import dataclass, field


@dataclass
class EpisodicMemory:
    """单条事件记忆"""
    timestamp: float
    description: str
    emotional_signature: dict    # {"joy": 0.8, "fear": 0.3, ...} 或 PAD
    significance: float          # 0.0-1.0
    event_type: str
    tags: list[str] = field(default_factory=list)
    internal_state_snapshot: dict = field(default_factory=dict)  # 当时的情感状态快照

    def age(self) -> float:
        """距离现在的秒数"""
        return time.time() - self.timestamp

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "description": self.description,
            "emotional_signature": self.emotional_signature,
            "significance": self.significance,
            "event_type": self.event_type,
            "tags": self.tags,
        }


class EpisodicMemoryStore:
    """事件记忆存储与检索"""

    def __init__(self, max_size: int = 100):
        self.memories: list[EpisodicMemory] = []
        self.max_size = max_size

    def store(self, memory: EpisodicMemory) -> None:
        """存储一条记忆，超出容量时淘汰最旧的"""
        self.memories.append(memory)
        if len(self.memories) > self.max_size:
            # 保留高显著性的记忆，淘汰最旧的低显著性记忆
            self.memories.sort(key=lambda m: (m.significance, m.timestamp), reverse=True)
            self.memories = self.memories[:self.max_size]

    def get_recent(self, n: int = 5) -> list[EpisodicMemory]:
        """获取最近的N条记忆"""
        sorted_mems = sorted(self.memories, key=lambda m: m.timestamp, reverse=True)
        return sorted_mems[:n]

    def get_significant(self, threshold: float = 0.5) -> list[EpisodicMemory]:
        """获取所有高显著性记忆"""
        return [m for m in self.memories if m.significance >= threshold]

    def get_by_emotion(self, target_emotion: str, n: int = 5) -> list[EpisodicMemory]:
        """获取与目标情绪最相似的记忆"""
        scored = []
        for m in self.memories:
            score = m.emotional_signature.get(target_emotion, 0.0)
            scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:n]]

    def get_by_tags(self, tags: list[str], n: int = 10) -> list[EpisodicMemory]:
        """按标签检索记忆"""
        scored = []
        for m in self.memories:
            overlap = len(set(tags) & set(m.tags))
            if overlap > 0:
                scored.append((overlap, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:n]]

    def get_by_type(self, event_type: str, n: int = 5) -> list[EpisodicMemory]:
        """获取同类型的历史事件"""
        matches = [m for m in self.memories if m.event_type == event_type]
        matches.sort(key=lambda m: m.timestamp, reverse=True)
        return matches[:n]

    def get_context_for_event(self, current_event_type: str, n: int = 5) -> list[dict]:
        """为当前事件检索相关记忆上下文。

        综合: 最近事件 + 同类型事件 + 高显著性事件
        """
        recent = self.get_recent(3)
        same_type = self.get_by_type(current_event_type, 3)
        significant = self.get_significant(0.6)

        # 去重合并
        seen = set()
        result = []
        for m in recent + same_type + significant:
            if id(m) not in seen:
                seen.add(id(m))
                result.append(m)
        return [m.to_dict() for m in result[:n]]

    def get_recent_descriptions(self, n: int = 5) -> list[str]:
        """获取最近N个事件的描述（用于context注入）"""
        return [m.description for m in self.get_recent(n)]

    def __len__(self) -> int:
        return len(self.memories)

    def to_dict(self) -> list[dict]:
        return [m.to_dict() for m in self.memories]

    @classmethod
    def from_dict_list(cls, data: list[dict]) -> "EpisodicMemoryStore":
        store = cls()
        for d in data:
            store.memories.append(EpisodicMemory(
                timestamp=d.get("timestamp", 0),
                description=d.get("description", ""),
                emotional_signature=d.get("emotional_signature", {}),
                significance=d.get("significance", 0.5),
                event_type=d.get("event_type", "unknown"),
                tags=d.get("tags", []),
            ))
        return store
