"""Long-Term Memory — 持久化记忆 + 时间衰减 + 情感索引 + 冲突检测。

从现有 episodic_memory.py 重构:
- 保留 EpisodicMemory dataclass (情感签名 + 显著性 + related_ids)
- 保留 hybrid search 接口框架
- 新增实际 embedding 函数注入
- 新增冲突检测 + 矛盾扫描 (参考 anda-hippocampus)
"""
from __future__ import annotations

import math
import sqlite3
import time

from .store import MemoryStore, MemoryRecord, ConsolidationReport


class LongTermMemory(MemoryStore):
    """长期记忆 — SQLite + 时间衰减 + 情感签名索引。

    容量 ~500 条。30 天半衰期。
    """

    def __init__(self, db_path: str = ":memory:", max_items: int = 500,
                 half_life_days: float = 30.0):
        self.db_path = db_path
        self.max_items = max_items
        self.half_life_days = half_life_days
        self._conn: sqlite3.Connection | None = None
        self._embedding_fn = None

    async def initialize(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS ltm (
                record_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                emotion TEXT DEFAULT '{}',
                significance REAL DEFAULT 0.5,
                event_type TEXT DEFAULT 'unknown',
                tags TEXT DEFAULT '[]',
                timestamp REAL,
                recall_count INTEGER DEFAULT 0,
                related_ids TEXT DEFAULT '[]',
                embedding BLOB,
                superseded INTEGER DEFAULT 0
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ltm_emotion ON ltm(event_type)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ltm_significance ON ltm(significance)
        """)
        self._conn.commit()

    def set_embedding_fn(self, fn):
        self._embedding_fn = fn

    async def store(self, record: MemoryRecord) -> str:
        import json

        rid = record.record_id or f"ltm_{int(time.time()*1000)}_{len(self)}"
        record.record_id = rid

        emb_blob = None
        if self._embedding_fn:
            try:
                emb = self._embedding_fn(record.content)
                import struct
                emb_blob = struct.pack(f'{len(emb)}f', *emb)
            except Exception:
                pass

        related = json.dumps(record.metadata.get("related_ids", []), ensure_ascii=False)

        self._conn.execute(
            "INSERT OR REPLACE INTO ltm VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (rid, record.content, json.dumps(record.emotional_signature, ensure_ascii=False),
             record.significance, record.event_type, json.dumps(record.tags, ensure_ascii=False),
             record.timestamp, record.recall_count, related, emb_blob, 0),
        )
        self._conn.commit()
        self._trim()
        return rid

    async def recall(self, query: str, n: int = 5) -> list[MemoryRecord]:
        """混合检索: 语义(0.3) + 时间衰减(0.3) + 显著性(0.4) + 类型加分。"""
        all_rows = self._conn.execute(
            "SELECT * FROM ltm WHERE superseded = 0 ORDER BY timestamp DESC LIMIT ?",
            (n * 5,),
        ).fetchall()

        now = time.time()
        scored: list[tuple[float, MemoryRecord]] = []

        for row in all_rows:
            r = self._row_to_record(row)
            sig_weight = r.significance * 0.4
            time_weight = self._time_decay(r, now) * 0.3

            # 语义相似度: 简单关键词匹配
            sem_weight = 0.0
            query_lower = query.lower()
            if query_lower in r.content.lower():
                sem_weight = 0.3
            else:
                keywords = query_lower.split()
                hits = sum(1 for kw in keywords if kw in r.content.lower())
                sem_weight = min(0.3, hits * 0.1)

            score = sem_weight + time_weight + sig_weight
            scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        for _, r in scored[:n]:
            self._conn.execute(
                "UPDATE ltm SET recall_count = recall_count + 1 WHERE record_id = ?",
                (r.record_id,),
            )
        self._conn.commit()
        return [r for _, r in scored[:n]]

    async def search(self, embedding=None, filters=None, n=5) -> list[MemoryRecord]:
        if filters and filters.get("query"):
            return await self.recall(filters["query"], n)
        return await self.recall("", n)

    async def consolidate(self) -> ConsolidationReport:
        """长期记忆巩固: 去重 + 关联检测。"""
        report = ConsolidationReport()
        # 检测相邻相似记忆（简易去重）
        rows = self._conn.execute(
            "SELECT record_id, content FROM ltm WHERE superseded = 0 "
            "ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        seen: set[str] = set()
        for rid, content in rows:
            # 简化: 完全相同内容标记为重复
            if content in seen:
                self._conn.execute(
                    "UPDATE ltm SET superseded = 1 WHERE record_id = ?", (rid,)
                )
                report.merged += 1
            seen.add(content)
        self._conn.commit()
        return report

    async def forget(self) -> int:
        """时间衰减淘汰: 30 天以上的低显著性记忆。"""
        cutoff = time.time() - self.half_life_days * 86400
        cursor = self._conn.execute(
            "DELETE FROM ltm WHERE timestamp < ? AND significance < 0.3",
            (cutoff,),
        )
        self._conn.commit()
        return cursor.rowcount

    def detect_contradictions(self) -> list[dict]:
        """矛盾检测 (参考 anda): 同实体、相反情感 → 标记冲突。"""
        import json
        conflicts = []
        rows = self._conn.execute(
            "SELECT * FROM ltm WHERE superseded = 0 ORDER BY timestamp DESC LIMIT 100"
        ).fetchall()

        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1 = self._row_to_record(rows[i])
                r2 = self._row_to_record(rows[j])
                # 检查情感对立 (positive vs negative)
                e1 = r1.emotional_signature
                e2 = r2.emotional_signature
                if (e1.get("joy", 0) > 0.5 and e2.get("sadness", 0) > 0.5) or \
                   (e1.get("trust", 0) > 0.5 and e2.get("fear", 0) > 0.5):
                    conflicts.append({
                        "record_a": r1.record_id,
                        "record_b": r2.record_id,
                        "type": "emotional_contradiction",
                    })
        return conflicts

    def promote_candidates(self) -> list[MemoryRecord]:
        """recall>=5 + sig>0.8 → 候选提升到 Core 图谱。"""
        rows = self._conn.execute(
            "SELECT * FROM ltm WHERE recall_count >= 5 AND significance >= 0.8 AND superseded = 0"
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def _time_decay(self, record: MemoryRecord, now: float) -> float:
        age_days = (now - record.timestamp) / 86400.0
        return math.exp(-age_days / self.half_life_days)

    def _trim(self):
        count = self._conn.execute("SELECT COUNT(*) FROM ltm").fetchone()[0]
        if count > self.max_items:
            excess = count - self.max_items
            self._conn.execute(
                "DELETE FROM ltm WHERE rowid IN ("
                "SELECT rowid FROM ltm ORDER BY significance ASC, timestamp ASC LIMIT ?)",
                (excess,),
            )
            self._conn.commit()

    def _row_to_record(self, row) -> MemoryRecord:
        import json
        return MemoryRecord(
            record_id=row[0], content=row[1],
            emotional_signature=json.loads(row[2]) if row[2] else {},
            significance=row[3], event_type=row[4],
            tags=json.loads(row[5]) if row[5] else [],
            timestamp=row[6], recall_count=row[7],
            metadata={
                "related_ids": json.loads(row[8]) if row[8] else [],
                "embedding": row[9],
                "superseded": bool(row[10]),
            },
        )

    async def on_session_end(self) -> None:
        if self._conn:
            self._conn.commit()

    async def shutdown(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def __len__(self) -> int:
        if self._conn:
            return self._conn.execute("SELECT COUNT(*) FROM ltm WHERE superseded = 0").fetchone()[0]
        return 0
