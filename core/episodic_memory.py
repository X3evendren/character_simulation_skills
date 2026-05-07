"""事件记忆 — Episodic Memory with Emotional Tagging

基于 AdaMem (2026), MENTOR (2026), MiroFish (2025), Hermes Agent (2025):
- 存储关键事件及其情感签名
- 时序关系边 — 因果相关事件链接 (MiroFish GraphRAG 启发)
- 优先级淘汰 — 显著性 + 新近度加权 (Hermes 启发)
- 冻结快照 — 会话开始时的记忆快照 (Hermes Frozen Snapshot)
- 提供 character_state 的 "long-term memory" 层
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
    internal_state_snapshot: dict = field(default_factory=dict)
    # 时序关系边 — 关联到因果相关的其他记忆ID (MiroFish 启发)
    related_ids: list[int] = field(default_factory=list)
    memory_id: int = 0

    def age(self) -> float:
        return time.time() - self.timestamp

    def importance_score(self) -> float:
        """重要性 = 显著性 × 0.7 + 新近度 × 0.3 (Hermes 优先级淘汰启发)"""
        recency = max(0, 1.0 - self.age() / (3600 * 24 * 30))  # 30天衰减
        return self.significance * 0.7 + recency * 0.3

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "description": self.description,
            "emotional_signature": self.emotional_signature,
            "significance": self.significance,
            "event_type": self.event_type,
            "tags": self.tags,
            "related_ids": self.related_ids,
            "memory_id": self.memory_id,
        }


class EpisodicMemoryStore:
    """事件记忆存储与检索 — 增强版"""

    def __init__(self, max_size: int = 100):
        self.memories: list[EpisodicMemory] = []
        self.max_size = max_size
        self._next_id = 1
        # 冻结快照 — 会话开始时捕获，不受后续写入影响 (Hermes 启发)
        self._snapshot: list[dict] | None = None

    # ═══ 存储 ═══

    def store(self, memory: EpisodicMemory) -> None:
        """存储一条记忆。超容量时按重要性淘汰。"""
        memory.memory_id = self._next_id
        self._next_id += 1

        # 检测时序关系：与最近记忆的因果关联
        if self.memories:
            last = self.memories[-1]
            if (memory.timestamp - last.timestamp < 3600  # 1小时内
                    and any(t in memory.tags for t in last.tags)):
                memory.related_ids.append(last.memory_id)
                last.related_ids.append(memory.memory_id)

        self.memories.append(memory)

        # 优先级淘汰：按重要性排序，淘汰最低分的
        if len(self.memories) > self.max_size:
            self.memories.sort(key=lambda m: m.importance_score(), reverse=True)
            self.memories = self.memories[:self.max_size]

    # ═══ 检索 ═══

    def get_recent(self, n: int = 5) -> list[EpisodicMemory]:
        sorted_mems = sorted(self.memories, key=lambda m: m.timestamp, reverse=True)
        return sorted_mems[:n]

    def get_significant(self, threshold: float = 0.5) -> list[EpisodicMemory]:
        return [m for m in self.memories if m.significance >= threshold]

    def get_by_emotion(self, target_emotion: str, n: int = 5) -> list[EpisodicMemory]:
        scored = []
        for m in self.memories:
            score = m.emotional_signature.get(target_emotion, 0.0)
            scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:n]]

    def get_by_tags(self, tags: list[str], n: int = 10) -> list[EpisodicMemory]:
        scored = []
        for m in self.memories:
            overlap = len(set(tags) & set(m.tags))
            if overlap > 0:
                scored.append((overlap, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:n]]

    def get_by_type(self, event_type: str, n: int = 5) -> list[EpisodicMemory]:
        matches = [m for m in self.memories if m.event_type == event_type]
        matches.sort(key=lambda m: m.timestamp, reverse=True)
        return matches[:n]

    def get_timeline(self, n: int = 10) -> list[dict]:
        """获取时序关系链 — 展示事件间的因果关联 (MiroFish 启发)"""
        recent = self.get_recent(n)
        timeline = []
        for m in recent:
            related = [r.description[:50]
                       for r in self.memories if r.memory_id in m.related_ids]
            entry = m.to_dict()
            entry["related_events"] = related
            timeline.append(entry)
        return timeline

    # ═══ 冻结快照 (Hermes 启发) ═══

    def freeze_snapshot(self) -> list[dict]:
        """冻结当前记忆快照。
        注意: orchestrator 当前使用 format_snapshot_for_prompt()
        直接读取实时记忆而非冻结快照。此方法作为显式会话起点的备选。
        """
        self._snapshot = [m.to_dict() for m in self.get_recent(5)]
        return self._snapshot

    def get_snapshot(self) -> list[dict]:
        """获取冻结快照。如果未冻结，自动冻结。"""
        if self._snapshot is None:
            self.freeze_snapshot()
        return self._snapshot

    def format_snapshot_for_prompt(self) -> str:
        """将冻结快照格式化为 prompt 可注入的文本。"""
        snap = self.get_snapshot()
        if not snap:
            return ""
        lines = ["[角色记忆 — 最近发生的事]"]
        for i, m in enumerate(snap, 1):
            lines.append(f"{i}. {m['description']}")
        return "\n".join(lines)

    # ═══ 上下文检索 ═══

    def get_context_for_event(self, current_event_type: str, n: int = 5) -> list[dict]:
        recent = self.get_recent(3)
        same_type = self.get_by_type(current_event_type, 3)
        significant = self.get_significant(0.6)

        seen = set()
        result = []
        for m in recent + same_type + significant:
            if id(m) not in seen:
                seen.add(id(m))
                result.append(m)
        return [m.to_dict() for m in result[:n]]

    def get_recent_descriptions(self, n: int = 5) -> list[str]:
        return [m.description for m in self.get_recent(n)]

    # ═══ 工具方法 ═══

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
                related_ids=d.get("related_ids", []),
                memory_id=d.get("memory_id", 0),
            ))
        store._next_id = max((m.memory_id for m in store.memories), default=0) + 1
        return store
