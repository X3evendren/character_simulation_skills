"""Short-Term Memory — SQLite + FTS5 全文检索。

参考 Hermes Holographic provider 的 SQLite FTS5 架构，
但用真实 embedding 替代 HRR 1024 维相位向量。
"""
from __future__ import annotations

import math
import sqlite3
import time
import os

from .store import MemoryStore, MemoryRecord, ConsolidationReport


class ShortTermMemory(MemoryStore):
    """短期记忆 — SQLite + FTS5 + embedding 缓存。

    容量 ~200 条。信任评分抄 Hermes: helpful +0.05, unhelpful -0.10。
    """

    def __init__(self, db_path: str = ":memory:", max_items: int = 200):
        self.db_path = db_path
        self.max_items = max_items
        self.trust_decay: float = 0.95
        self._conn: sqlite3.Connection | None = None
        self._embedding_fn = None  # 可选: (text: str) -> list[float]

    async def initialize(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS stm (
                record_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                emotion TEXT DEFAULT '{}',
                significance REAL DEFAULT 0.5,
                event_type TEXT DEFAULT 'unknown',
                tags TEXT DEFAULT '[]',
                timestamp REAL,
                trust REAL DEFAULT 1.0,
                recall_count INTEGER DEFAULT 0,
                embedding BLOB
            )
        """)
        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS stm_fts USING fts5(
                content, event_type, tags, content=stm, content_rowid=rowid
            )
        """)
        self._conn.commit()

    def set_embedding_fn(self, fn):
        self._embedding_fn = fn

    async def store(self, record: MemoryRecord) -> str:
        rid = record.record_id or f"stm_{int(time.time()*1000)}_{len(self)}"
        record.record_id = rid

        emb_blob = None
        if self._embedding_fn:
            try:
                emb = self._embedding_fn(record.content)
                import struct
                emb_blob = struct.pack(f'{len(emb)}f', *emb)
            except Exception:
                pass

        import json
        self._conn.execute(
            "INSERT OR REPLACE INTO stm VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rid, record.content, json.dumps(record.emotional_signature, ensure_ascii=False),
             record.significance, record.event_type, json.dumps(record.tags, ensure_ascii=False),
             record.timestamp, record.trust, record.recall_count, emb_blob),
        )
        self._conn.commit()
        self._trim()
        return rid

    async def recall(self, query: str, n: int = 5) -> list[MemoryRecord]:
        """FTS5 全文检索 → embedding 重排序 → 信任加权。"""
        import json

        # FTS5 搜索
        rows = self._conn.execute(
            "SELECT rowid FROM stm_fts WHERE stm_fts MATCH ? LIMIT ?",
            (query, n * 3),
        ).fetchall()

        if not rows:
            # 回退: 按时间取最近
            rows = self._conn.execute(
                "SELECT rowid FROM stm ORDER BY timestamp DESC LIMIT ?",
                (n,),
            ).fetchall()

        rowids = [r[0] for r in rows]
        results = []
        for rid in rowids:
            row = self._conn.execute(
                "SELECT * FROM stm WHERE rowid=?", (rid,)
            ).fetchone()
            if row:
                results.append(self._row_to_record(row))

        # 信任加权排序
        results.sort(key=lambda r: r.trust * r.significance, reverse=True)
        return results[:n]

    async def search(self, embedding=None, filters=None, n=5) -> list[MemoryRecord]:
        """混合检索: FTS5 + 可选 embedding 相似度。"""
        import json

        if embedding and self._embedding_fn:
            # 有 embedding → 全量扫描计算余弦相似度
            all_rows = self._conn.execute("SELECT * FROM stm").fetchall()
            scored = []
            for row in all_rows:
                r = self._row_to_record(row)
                if filters and filters.get("event_type") and r.event_type != filters["event_type"]:
                    continue
                sim = self._cosine_sim(embedding, r) if r.metadata.get("embedding") else 0.0
                score = sim * 0.4 + r.significance * 0.3 + r.trust * 0.3
                scored.append((score, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [r for _, r in scored[:n]]

        # 无 embedding → FTS5
        query = filters.get("query", "") if filters else ""
        if query:
            return await self.recall(query, n)
        return await self.recall("", n)

    async def consolidate(self) -> ConsolidationReport:
        """短期记忆巩固: 信任衰减 + 提升候选。"""
        report = ConsolidationReport()
        # 信任衰减
        self._conn.execute("UPDATE stm SET trust = trust * ?", (self.trust_decay,))
        self._conn.commit()
        return report

    async def forget(self) -> int:
        """信任评分 < 0.1 的记录淘汰。"""
        cursor = self._conn.execute("DELETE FROM stm WHERE trust < 0.1")
        self._conn.commit()
        return cursor.rowcount

    def record_feedback(self, record_id: str, helpful: bool):
        """信任评分 (抄 Hermes): helpful +0.05, unhelpful -0.10。"""
        delta = 0.05 if helpful else -0.10
        self._conn.execute(
            "UPDATE stm SET trust = MAX(0.0, MIN(1.0, trust + ?)) WHERE record_id = ?",
            (delta, record_id),
        )
        # 提升 recall_count
        self._conn.execute(
            "UPDATE stm SET recall_count = recall_count + 1 WHERE record_id = ?",
            (record_id,),
        )
        self._conn.commit()

    def promote_candidates(self) -> list[MemoryRecord]:
        """recall>=3 → 候选提升到 LTM。"""
        rows = self._conn.execute(
            "SELECT * FROM stm WHERE recall_count >= 3"
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def _trim(self):
        count = self._conn.execute("SELECT COUNT(*) FROM stm").fetchone()[0]
        if count > self.max_items:
            excess = count - self.max_items
            self._conn.execute(
                "DELETE FROM stm WHERE rowid IN ("
                "SELECT rowid FROM stm ORDER BY trust ASC, timestamp ASC LIMIT ?)",
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
            timestamp=row[6], trust=row[7], recall_count=row[8],
            metadata={"embedding": row[9]} if row[9] else {},
        )

    @staticmethod
    def _cosine_sim(a: list[float], record: MemoryRecord) -> float:
        emb = record.metadata.get("embedding")
        if not emb or not a:
            return 0.0
        import struct
        if isinstance(emb, bytes):
            n = len(emb) // 4
            emb_list = list(struct.unpack(f'{n}f', emb))
        else:
            emb_list = emb
        if len(a) != len(emb_list):
            return 0.0
        dot = sum(x * y for x, y in zip(a, emb_list))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in emb_list))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

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
            return self._conn.execute("SELECT COUNT(*) FROM stm").fetchone()[0]
        return 0
