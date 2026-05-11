"""Core Graph Memory — 核心图谱记忆。

实体关系网络——从现有 graph_memory.py 重写:
- 三元组提取: LLM 辅助（非纯正则）
- 索引缓存滚动窗口 (参考 anda-hippocampus)
- BFS 子图查询 + 时间衰减
- 实体演化追踪 (superseded 标记，参考 anda)
"""
from __future__ import annotations

import math
import re
import sqlite3
import time

from .store import MemoryStore, MemoryRecord, ConsolidationReport


class CoreGraphMemory(MemoryStore):
    """核心图谱记忆 — 实体关系网络 + LLM 辅助抽取。

    容量: ~500 节点, ~2000 边。
    索引缓存: 滚动窗口避免全图遍历。
    """

    def __init__(self, db_path: str = ":memory:",
                 max_nodes: int = 500, max_edges: int = 2000,
                 half_life_days: float = 30.0):
        self.db_path = db_path
        self.max_nodes = max_nodes
        self.max_edges = max_edges
        self.half_life_days = half_life_days
        self._conn: sqlite3.Connection | None = None
        self._index_cache: dict[str, list] = {}  # entity → subgraph 缓存

    async def initialize(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT DEFAULT 'concept',
                label TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                created_at REAL,
                updated_at REAL,
                superseded INTEGER DEFAULT 0
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                timestamp REAL,
                source_event TEXT DEFAULT '',
                superseded INTEGER DEFAULT 0,
                FOREIGN KEY(from_id) REFERENCES nodes(node_id),
                FOREIGN KEY(to_id) REFERENCES nodes(node_id)
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)")
        self._conn.commit()

    async def store(self, record: MemoryRecord) -> str:
        """存储记忆 → 自动提取三元组并写入图谱。"""
        rid = record.record_id or f"core_{int(time.time()*1000)}"
        # 提取三元组
        triples = self._extract_triples(record.content)
        now = time.time()

        for subj, rel, obj in triples:
            subj_id = self._upsert_node(subj, self._infer_type(subj), now)
            obj_id = self._upsert_node(obj, self._infer_type(obj), now)
            self._add_edge(subj_id, obj_id, rel, now, record.content[:100])

        # 清除相关缓存
        for _, _, obj in triples:
            self._index_cache.pop(obj, None)
        for subj, _, _ in triples:
            self._index_cache.pop(subj, None)

        self._trim()
        return rid

    async def ingest_with_llm(self, event_text: str, provider, self_name: str = "") -> list[tuple]:
        """LLM 辅助实体抽取——低频调用，批量处理。

        使用心理引擎的小模型提取实体关系，
        比纯正则提取更准确。
        """
        prompt = f"""从以下事件文本中提取实体关系三元组。
格式: (主语, 关系, 宾语)

事件: {event_text}

输出 JSON 数组:
[["主语", "关系", "宾语"], ...]

只输出 JSON，不要其他内容。"""

        try:
            response = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=300,
            )
            from ..json_parser import extract_json
            data = extract_json(response.content)
            if isinstance(data, list):
                triples = []
                for item in data:
                    if isinstance(item, list) and len(item) >= 3:
                        triples.append((str(item[0]), str(item[1]), str(item[2])))
                return triples
        except Exception:
            pass

        # 回退到规则提取
        return self._extract_triples(event_text, self_name)

    def query_subgraph(self, entity: str, depth: int = 2) -> dict:
        """BFS 子图查询。

        先查索引缓存 → 命中直接返回 → 未命中遍历图。
        """
        cache_key = f"{entity}_d{depth}"
        if cache_key in self._index_cache:
            return self._index_cache[cache_key]

        # 查找匹配节点
        node_rows = self._conn.execute(
            "SELECT node_id, label, node_type FROM nodes WHERE label LIKE ? AND superseded = 0",
            (f"%{entity}%",),
        ).fetchall()

        if not node_rows:
            return {"nodes": [], "edges": [], "summary": f"未找到'{entity}'的相关信息"}

        node_ids = [r[0] for r in node_rows]
        visited = set(node_ids)
        relevant_edges = []
        frontier = list(node_ids)

        for _ in range(depth):
            next_frontier = []
            placeholders = ",".join("?" * len(frontier))
            edge_rows = self._conn.execute(
                f"SELECT * FROM edges WHERE (from_id IN ({placeholders}) OR to_id IN ({placeholders})) AND superseded = 0",
                frontier + frontier,
            ).fetchall()
            for er in edge_rows:
                relevant_edges.append(er)
                if er[1] not in visited:
                    visited.add(er[1])
                    next_frontier.append(er[1])
                if er[2] not in visited:
                    visited.add(er[2])
                    next_frontier.append(er[2])
            frontier = next_frontier

        # 时间衰减
        now = time.time()
        decayed_edges = []
        for er in relevant_edges:
            days = (now - er[5]) / 86400.0
            weight = er[4] * math.exp(-days / self.half_life_days)
            if weight > 0.1:
                decayed_edges.append({
                    "from": er[1], "to": er[2], "relation": er[3],
                    "weight": round(weight, 2), "source": er[6],
                })

        node_data = []
        for nid in visited:
            nr = self._conn.execute(
                "SELECT node_id, label, node_type FROM nodes WHERE node_id = ?", (nid,)
            ).fetchone()
            if nr:
                node_data.append({"id": nr[0], "label": nr[1], "type": nr[2]})

        # 生成摘要
        summary_parts = []
        for e in decayed_edges[:10]:
            from_label = next((n["label"] for n in node_data if n["id"] == e["from"]), e["from"])
            to_label = next((n["label"] for n in node_data if n["id"] == e["to"]), e["to"])
            summary_parts.append(f"{from_label}与{to_label}: {e['relation']}")

        result = {
            "nodes": node_data,
            "edges": decayed_edges,
            "summary": "; ".join(summary_parts) if summary_parts else "无显著关系",
        }

        # 缓存结果
        self._index_cache[cache_key] = result
        if len(self._index_cache) > 100:
            # 淘汰最旧的缓存项
            oldest = sorted(self._index_cache.keys())[:20]
            for k in oldest:
                del self._index_cache[k]

        return result

    def _extract_triples(self, text: str, self_name: str = "") -> list[tuple]:
        """规则三元组提取——零 Token 后备方案。"""
        triples = []

        # 模式1: 人名交互
        person_pattern = re.findall(r'([一-鿿]{1,4})(?:对|向|给|和|跟)([一-鿿]{1,4})', text)
        for subj, obj in person_pattern:
            if any(w in text for w in ["没", "不", "拒绝"]):
                triples.append((subj, "negative_interaction", obj))
            else:
                triples.append((subj, "interaction", obj))

        # 模式2: 情感表达式
        emotions = re.findall(r'(?:感到|觉得|很|非常|有点)(开心|难过|悲伤|愤怒|恐惧|焦虑|紧张|幸福|失落|失望|孤独)', text)
        for em in emotions:
            triples.append(("角色", "feels", em))

        return triples

    def _upsert_node(self, label: str, node_type: str, now: float) -> str:
        node_id = f"{node_type}_{label}"
        existing = self._conn.execute(
            "SELECT node_id FROM nodes WHERE node_id = ?", (node_id,)
        ).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE nodes SET updated_at = ? WHERE node_id = ?", (now, node_id)
            )
        else:
            self._conn.execute(
                "INSERT INTO nodes VALUES (?,?,?,?,?,?,?)",
                (node_id, node_type, label, "{}", now, now, 0),
            )
        self._conn.commit()
        return node_id

    def _add_edge(self, from_id: str, to_id: str, relation: str, now: float, source: str):
        existing = self._conn.execute(
            "SELECT edge_id, weight FROM edges WHERE from_id=? AND to_id=? AND relation=? AND superseded=0",
            (from_id, to_id, relation),
        ).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE edges SET weight=MIN(1.0, ?), timestamp=? WHERE edge_id=?",
                (existing[1] + 0.2, now, existing[0]),
            )
        else:
            self._conn.execute(
                "INSERT INTO edges (from_id, to_id, relation, weight, timestamp, source_event) VALUES (?,?,?,?,?,?)",
                (from_id, to_id, relation, 0.5, now, source),
            )
        self._conn.commit()

    @staticmethod
    def _infer_type(label: str) -> str:
        emotion_set = {"开心","难过","悲伤","愤怒","恐惧","焦虑","幸福","失落","孤独","紧张","失望"}
        if label in emotion_set:
            return "emotion"
        if len(label) <= 4 and all('一' <= c <= '鿿' for c in label):
            return "person"
        return "concept"

    def _trim(self):
        node_count = self._conn.execute("SELECT COUNT(*) FROM nodes WHERE superseded=0").fetchone()[0]
        if node_count > self.max_nodes:
            excess = node_count - self.max_nodes
            self._conn.execute(
                "UPDATE nodes SET superseded=1 WHERE node_id IN ("
                "SELECT node_id FROM nodes WHERE superseded=0 ORDER BY updated_at ASC LIMIT ?)",
                (excess,),
            )
        edge_count = self._conn.execute("SELECT COUNT(*) FROM edges WHERE superseded=0").fetchone()[0]
        if edge_count > self.max_edges:
            excess = edge_count - self.max_edges
            self._conn.execute(
                "UPDATE edges SET superseded=1 WHERE edge_id IN ("
                "SELECT edge_id FROM edges WHERE superseded=0 ORDER BY weight ASC LIMIT ?)",
                (excess,),
            )
        self._conn.commit()

    async def recall(self, query: str, n: int = 5) -> list[MemoryRecord]:
        subgraph = self.query_subgraph(query, depth=1)
        if subgraph.get("summary"):
            return [MemoryRecord(
                record_id=f"core_{int(time.time())}",
                content=subgraph["summary"],
                event_type="graph_query",
                significance=0.5,
            )]
        return []

    async def search(self, embedding=None, filters=None, n=5) -> list[MemoryRecord]:
        return await self.recall(filters.get("query", "") if filters else "", n)

    async def consolidate(self) -> ConsolidationReport:
        return ConsolidationReport()

    async def forget(self) -> int:
        cutoff = time.time() - self.half_life_days * 86400
        cursor = self._conn.execute(
            "UPDATE edges SET superseded=1 WHERE timestamp < ? AND weight < 0.2",
            (cutoff,),
        )
        self._conn.commit()
        return cursor.rowcount

    def evolve_entity(self, old_label: str, new_label: str):
        """实体演化: 旧标签标记 superseded，保留演化轨迹 (参考 anda)。"""
        self._conn.execute(
            "UPDATE nodes SET superseded=1 WHERE label=? AND superseded=0",
            (old_label,),
        )
        self._index_cache.clear()

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
            return self._conn.execute("SELECT COUNT(*) FROM nodes WHERE superseded=0").fetchone()[0]
        return 0
