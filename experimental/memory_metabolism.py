"""Memory Metabolism — 五级记忆代谢系统。

Working → Short-term → Long-term → Core (永久)
                                → Archive (淘汰)

Hermes 三层架构:
  Layer 1: soul.md + memory_index.md (黄金指针, 纯文本, 无检索)
  Layer 2: fact_store + skills (关键词/tag 检索)
  Layer 3: 语义向量 + 时间线索引 (高投资分析)
"""
from __future__ import annotations

import time
import math
from dataclasses import dataclass, field


# ═══ 记忆条目 ═══

@dataclass
class MemoryEntry:
    """单条记忆, 可在五级之间流动。"""
    memory_id: int
    content: str                    # 摘要/内容
    emotional_signature: dict       # {emotion: intensity}
    significance: float             # 0-1
    created_at: float               # 首次记录时间
    last_recalled_at: float         # 最后被召回的时间
    recall_count: int = 0           # 被召回次数
    tags: list[str] = field(default_factory=list)
    tier: str = "short"             # working / short / long / core / archive
    pointer_in_index: bool = False  # 是否在 memory_index.md 中

    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def days_since_recall(self) -> float:
        return (time.time() - self.last_recalled_at) / 86400.0

    def importance_score(self) -> float:
        """重要性 = 显著性×0.7 + 新近度×0.3"""
        recency = max(0.0, 1.0 - self.age_seconds() / (86400 * 30))
        return self.significance * 0.7 + recency * 0.3

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "emotional_signature": self.emotional_signature,
            "significance": self.significance,
            "created_at": self.created_at,
            "last_recalled_at": self.last_recalled_at,
            "recall_count": self.recall_count,
            "tags": self.tags,
            "tier": self.tier,
            "pointer_in_index": self.pointer_in_index,
        }


# ═══ 五级记忆存储 ═══

class MemoryMetabolism:
    """管理记忆在五级之间的流动。

    新陈代谢规则:
    - working→short: 情感强度>0.4 或 significance>0.3
    - short→long: 被召回≥3次 或 与核心相关
    - short→archive: 30天未召回 且 significance<0.5
    - long→core: 反复激活 且 与 soul 核心直接相关
    - long→archive: 90天未召回
    - core: 永久, 不可淘汰
    """

    def __init__(self, max_working: int = 20, max_short: int = 100,
                 max_long: int = 500, max_core: int = 20):
        self.working: list[MemoryEntry] = []     # 工作记忆
        self.short_term: list[MemoryEntry] = []   # 短期记忆
        self.long_term: list[MemoryEntry] = []    # 长期记忆
        self.core: list[MemoryEntry] = []         # 核心记忆
        self.archive: list[MemoryEntry] = []      # 淘汰归档

        self.max_working = max_working
        self.max_short = max_short
        self.max_long = max_long
        self.max_core = max_core

        self._next_id = 1

        # 淘汰日志
        self.elimination_log: list[dict] = []

        # 成长日记
        self.growth_log: list[dict] = []

        # 核心身份标记 (从 soul.md 提取)
        self.core_identity_keywords: list[str] = []

    # ═══ 摄入: 新体验进入 Working ═══

    def ingest(self, content: str, emotional_signature: dict,
               significance: float = 0.5, tags: list[str] | None = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=self._next_id,
            content=content[:300],
            emotional_signature=emotional_signature,
            significance=significance,
            created_at=time.time(),
            last_recalled_at=time.time(),
            tags=tags or [],
            tier="working",
        )
        self._next_id += 1
        self.working.append(entry)
        self._trim_tier("working")
        return entry

    # ═══ 代谢: 根据规则升级/淘汰 ═══

    def metabolize(self) -> dict:
        """运行一次新陈代谢周期。返回变更摘要。"""
        promotions = {"working→short": 0, "short→long": 0,
                       "long→core": 0, "short→archive": 0, "long→archive": 0}
        now = time.time()

        # Working → Short (情感强度>0.4 或 significance>0.3)
        survivors = []
        for m in self.working:
            max_emo = max(m.emotional_signature.values()) if m.emotional_signature else 0
            if max_emo > 0.4 or m.significance > 0.3:
                m.tier = "short"
                m.last_recalled_at = now
                self.short_term.append(m)
                promotions["working→short"] += 1
            else:
                survivors.append(m)  # 不够显著, 保留在 working 等待更多上下文
        self.working = survivors
        self._trim_tier("short")

        # Short → Long (被召回≥3次 或 与核心相关)
        survivors = []
        for m in self.short_term:
            is_core_related = any(kw in m.content for kw in self.core_identity_keywords)
            if m.recall_count >= 3 or is_core_related:
                m.tier = "long"
                self.long_term.append(m)
                promotions["short→long"] += 1
            # Short → Archive (30天未召回 且 significance<0.5)
            elif m.days_since_recall() > 30 and m.significance < 0.5:
                m.tier = "archive"
                self.archive.append(m)
                self.elimination_log.append({
                    "t": now, "memory_id": m.memory_id,
                    "reason": "30天未召回且低显著性",
                    "content": m.content[:80],
                })
                promotions["short→archive"] += 1
            else:
                survivors.append(m)  # 保持在 short
        self.short_term = survivors
        self._trim_tier("long")

        # Long → Core (与 soul 核心高度相关 + 反复激活)
        survivors = []
        for m in self.long_term:
            core_match_count = sum(1 for kw in self.core_identity_keywords if kw in m.content)
            if core_match_count >= 2 and m.recall_count >= 5:
                m.tier = "core"
                m.pointer_in_index = True
                self.core.append(m)
                promotions["long→core"] += 1
            # Long → Archive (90天未召回)
            elif m.days_since_recall() > 90:
                m.tier = "archive"
                self.archive.append(m)
                self.elimination_log.append({
                    "t": now, "memory_id": m.memory_id,
                    "reason": "90天未召回",
                    "content": m.content[:80],
                })
                promotions["long→archive"] += 1
            else:
                survivors.append(m)
        self.long_term = survivors
        self._trim_tier("core")

        # 生成成长日记
        self._maybe_generate_growth_log(promotions)

        return promotions

    # ═══ 召回 ═══

    def recall(self, memory_id: int) -> MemoryEntry | None:
        """召回一条记忆, 更新召回计数。"""
        for tier_list in [self.working, self.short_term, self.long_term, self.core]:
            for m in tier_list:
                if m.memory_id == memory_id:
                    m.last_recalled_at = time.time()
                    m.recall_count += 1
                    return m
        return None

    def search_by_tags(self, tags: list[str], n: int = 5) -> list[MemoryEntry]:
        """Layer 2: tag 检索。"""
        scored = []
        for tier_list in [self.short_term, self.long_term, self.core]:
            for m in tier_list:
                overlap = len(set(tags) & set(m.tags))
                if overlap > 0:
                    scored.append((overlap, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:n]]

    def search_by_time(self, start_t: float, end_t: float) -> list[MemoryEntry]:
        """Layer 3: 时间线检索。"""
        results = []
        for tier_list in [self.working, self.short_term, self.long_term, self.core, self.archive]:
            for m in tier_list:
                if start_t <= m.created_at <= end_t:
                    results.append(m)
        results.sort(key=lambda m: m.created_at)
        return results

    def search_semantic(self, query_embedding, n: int = 5) -> list[MemoryEntry]:
        """Layer 3: 语义检索 (需要外部嵌入)。占位——返回 tag 匹配作为回退。"""
        # 真实实现需要向量数据库; 当前回退到 tag 匹配
        return []

    # ═══ 指针管理 (Layer 1) ═══

    def build_memory_index(self) -> str:
        """生成 memory_index.md 的内容——纯指针列表。"""
        lines = ["# Memory Index", "",
                 "> 这是记忆指针索引。实际内容在对应的存储层中。",
                 "> 格式: {id} | {title} | {emotional_tag} | {time}", ""]
        for m in self.core + self.long_term[:10]:
            if m.pointer_in_index or m.tier == "core":
                dominant = max(m.emotional_signature.items(), key=lambda x: x[1])[0] if m.emotional_signature else "neutral"
                t = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.created_at))
                lines.append(f"- [{m.memory_id}] {m.content[:60]} | {dominant} | {t}")
        return "\n".join(lines)

    def build_growth_log(self) -> str:
        """生成成长日志。"""
        if not self.growth_log:
            return "# Growth Log\n\n暂无成长记录"
        lines = ["# Growth Log", ""]
        for entry in self.growth_log[-20:]:
            t = time.strftime("%Y-%m-%d", time.localtime(entry.get("t", 0)))
            lines.append(f"## {t}")
            lines.append(f"学会了: {entry.get('what_i_learned', '')}")
            lines.append(f"如何改变: {entry.get('how_i_changed', '')}")
            lines.append("")
        return "\n".join(lines)

    # ═══ 噪音率 ═══

    def noise_ratio(self) -> float:
        """计算当前上下文的噪音率。"""
        total = len(self.working) + len(self.short_term) + len(self.long_term)
        if total == 0:
            return 0.0
        # 噪音 = 低显著性 + 过期短时 + 归档候选
        noisy = 0
        for m in self.working:
            max_emo = max(m.emotional_signature.values()) if m.emotional_signature else 0
            if m.significance < 0.3 and max_emo < 0.3:
                noisy += 1
        for m in self.short_term:
            if m.days_since_recall() > 20:
                noisy += 1
        return noisy / total

    def noise_report(self) -> dict:
        """生成噪音报告。"""
        return {
            "noise_ratio": round(self.noise_ratio(), 2),
            "total_memories": len(self.working) + len(self.short_term) + len(self.long_term),
            "working_count": len(self.working),
            "short_count": len(self.short_term),
            "long_count": len(self.long_term),
            "core_count": len(self.core),
            "archive_count": len(self.archive),
            "elimination_log_size": len(self.elimination_log),
        }

    # ═══ 内部 ═══

    def _trim_tier(self, tier: str):
        tier_map = {"working": (self.working, self.max_working),
                     "short": (self.short_term, self.max_short),
                     "long": (self.long_term, self.max_long),
                     "core": (self.core, self.max_core)}
        if tier in tier_map:
            items, max_size = tier_map[tier]
            if len(items) > max_size:
                items.sort(key=lambda m: m.importance_score(), reverse=True)
                overflow = items[max_size:]
                items[:] = items[:max_size]
                for m in overflow:
                    m.tier = "archive"
                    self.archive.append(m)
                    self.elimination_log.append({
                        "t": time.time(), "memory_id": m.memory_id,
                        "reason": f"{tier}容量溢出",
                        "content": m.content[:80],
                    })

    def _maybe_generate_growth_log(self, promotions: dict):
        total_promotions = sum(promotions.values())
        if total_promotions < 3:
            return
        new_long = promotions.get("short→long", 0) + promotions.get("long→core", 0)
        if new_long < 3:
            return
        # 生成成长记录
        recent_long = [m for m in self.long_term[-new_long:]]
        learned = " ".join(m.content[:50] for m in recent_long[:3])
        self.growth_log.append({
            "t": time.time(),
            "what_i_learned": f"从最近的经历中学会了: {learned}",
            "how_i_changed": f"记忆系统已将{new_long}条记忆从短期升级为长期存储",
        })

    def to_dict(self) -> dict:
        return {
            "working": [m.to_dict() for m in self.working],
            "short_term": [m.to_dict() for m in self.short_term],
            "long_term": [m.to_dict() for m in self.long_term],
            "core": [m.to_dict() for m in self.core],
            "archive": [m.to_dict() for m in self.archive],
            "elimination_log": self.elimination_log[-50:],
            "growth_log": self.growth_log[-20:],
            "core_identity_keywords": self.core_identity_keywords,
        }

    # ═══ 文件 I/O: soul.md + memory_index.md ═══

    def set_soul(self, content: str):
        """设置 soul.md 内容 (核心身份)。"""
        self._soul_content = content
        # 从 soul 内容提取核心身份关键词
        keywords = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                word = line[2:].strip()
                if len(word) >= 2:
                    keywords.append(word)
        self.core_identity_keywords = keywords

    def get_soul(self) -> str:
        return getattr(self, "_soul_content", "")

    def write_to_disk(self, base_dir: str):
        """将 soul.md 和 memory_index.md 写入磁盘。"""
        import os
        os.makedirs(base_dir, exist_ok=True)

        soul_path = os.path.join(base_dir, "soul.md")
        with open(soul_path, "w", encoding="utf-8") as f:
            f.write(self.get_soul() or "# Soul\n\n角色核心身份未定义。")

        index_path = os.path.join(base_dir, "memory_index.md")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(self.build_memory_index())

        # 成长日记
        growth_path = os.path.join(base_dir, "growth_log.md")
        with open(growth_path, "w", encoding="utf-8") as f:
            f.write(self.build_growth_log())

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryMetabolism":
        mm = cls()
        for tier, entries in [
            ("working", data.get("working", [])),
            ("short_term", data.get("short_term", [])),
            ("long_term", data.get("long_term", [])),
            ("core", data.get("core", [])),
            ("archive", data.get("archive", [])),
        ]:
            target = getattr(mm, tier)
            for d in entries:
                target.append(MemoryEntry(
                    memory_id=d["memory_id"], content=d["content"],
                    emotional_signature=d.get("emotional_signature", {}),
                    significance=d.get("significance", 0.5),
                    created_at=d.get("created_at", 0),
                    last_recalled_at=d.get("last_recalled_at", 0),
                    recall_count=d.get("recall_count", 0),
                    tags=d.get("tags", []), tier=d.get("tier", tier),
                    pointer_in_index=d.get("pointer_in_index", False),
                ))
        mm._next_id = max((m.memory_id for tier_list in [mm.working, mm.short_term, mm.long_term, mm.core, mm.archive] for m in tier_list), default=0) + 1
        mm.elimination_log = data.get("elimination_log", [])
        mm.growth_log = data.get("growth_log", [])
        mm.core_identity_keywords = data.get("core_identity_keywords", [])
        return mm
