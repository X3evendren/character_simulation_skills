"""Working Memory — 当前上下文窗口。

认知负荷滑动窗口，非简单 FIFO。
- 高显著性事件 (sig>0.7): 锁定不淘汰
- 未完成的任务: 锁定不淘汰
- 低显著性 + 低情感 + 旧: 优先淘汰
"""
from __future__ import annotations

import time
from collections import OrderedDict

from .store import MemoryStore, MemoryRecord, ConsolidationReport


class WorkingMemory(MemoryStore):
    """当前工作记忆 — 认知负荷滑动窗口。

    纯内存操作，零 I/O 延迟。
    """

    def __init__(self, capacity: int = 50):
        self.capacity = capacity
        self._records: OrderedDict[str, MemoryRecord] = OrderedDict()
        self._locked: set[str] = set()         # 锁定项 ID
        self._next_id: int = 1

    async def store(self, record: MemoryRecord) -> str:
        rid = record.record_id or f"wm_{self._next_id}"
        self._next_id += 1
        record.record_id = rid

        self._records[rid] = record
        self._records.move_to_end(rid)

        # 高显著性事件锁定
        if record.significance >= 0.7:
            self._locked.add(rid)

        if len(self._records) > self.capacity:
            self._evict()

        return rid

    async def recall(self, query: str, n: int = 5) -> list[MemoryRecord]:
        """直接遍历窗口搜索（内存操作，零延迟）。

        优先匹配:
        1. 精确关键词匹配
        2. 内容包含查询关键词
        3. 按时间倒序
        """
        query_lower = query.lower()
        scored: list[tuple[float, MemoryRecord]] = []

        for r in self._records.values():
            score = 0.0
            content = r.content.lower()
            # 精确匹配
            if query_lower in content:
                score += 0.5
            # 关键词匹配
            keywords = query_lower.split()
            score += sum(0.1 for kw in keywords if kw in content)
            # 情感标签匹配
            if query_lower in r.emotional_signature:
                score += 0.3
            # 显著性加成
            score += r.significance * 0.2
            # 锁定加成
            if r.record_id in self._locked:
                score += 0.2
            scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:n]]

    async def search(self, embedding=None, filters=None, n=5) -> list[MemoryRecord]:
        """工作记忆不支持 embedding 搜索，回退到标签过滤。"""
        if filters:
            results = []
            for r in self._records.values():
                if any(tag in filters.get("tags", []) for tag in r.tags):
                    results.append(r)
                elif filters.get("event_type") and r.event_type == filters["event_type"]:
                    results.append(r)
            return results[:n]
        return list(self._records.values())[-n:]

    async def consolidate(self) -> ConsolidationReport:
        """工作记忆不自行巩固——由代谢引擎处理。"""
        return ConsolidationReport()

    async def forget(self) -> int:
        """强制淘汰低优先级项。"""
        before = len(self._records)
        to_remove = max(0, len(self._records) - self.capacity)
        removed = 0
        for rid in list(self._records.keys()):
            if removed >= to_remove:
                break
            if rid not in self._locked:
                del self._records[rid]
                removed += 1
        return before - len(self._records)

    def _evict(self):
        """认知负荷淘汰: 低显著性 + 低情感 + 旧 → 优先"""
        candidates = [
            (r.significance + sum(r.emotional_signature.values()), rid)
            for rid, r in self._records.items()
            if rid not in self._locked
        ]
        candidates.sort(key=lambda x: x[0])  # 最低分数优先淘汰

        for _, rid in candidates[:max(1, len(self._records) - self.capacity)]:
            del self._records[rid]

    def unlock(self, record_id: str):
        """解锁一个记录（任务完成等）。"""
        self._locked.discard(record_id)

    def get_locked(self) -> list[MemoryRecord]:
        """获取所有锁定的记录。"""
        return [self._records[rid] for rid in self._locked if rid in self._records]

    def promote_candidates(self) -> list[MemoryRecord]:
        """返回应该提升到 STM 的记录 (sig>0.3 or emotion>0.4)。"""
        result = []
        for r in self._records.values():
            if r.significance > 0.3 or max(r.emotional_signature.values(), default=0) > 0.4:
                result.append(r)
        return result

    def __len__(self) -> int:
        return len(self._records)
