"""Sleep Cycle 代谢引擎 — 后台记忆代谢。

参考 anda-hippocampus 的三段式睡眠周期。
这是本记忆系统与 LangMem/Mem0 等产品的最大区别:
不是简单的 CRUD，而是带"代谢"的生命系统。

Daydream: 闲置期微合并 (每 10 tick)
Quick Sleep: 去重 + 信任衰减 (每 50 tick)
Full Sleep: 矛盾检测 + 实体演化 + 索引重建 (每会话结束)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .store import ConsolidationReport
from .working import WorkingMemory
from .short_term import ShortTermMemory
from .long_term import LongTermMemory


@dataclass
class MetabolismStats:
    """代谢统计"""
    daydream_count: int = 0
    quick_sleep_count: int = 0
    full_sleep_count: int = 0
    total_merged: int = 0
    total_promoted: int = 0
    total_archived: int = 0
    total_conflicts: int = 0
    last_daydream: float = 0.0
    last_quick: float = 0.0
    last_full: float = 0.0


class SleepCycleMetabolism:
    """后台记忆代谢引擎 — 三段式睡眠周期。

    用法:
        metabolism = SleepCycleMetabolism(working, stm, ltm, core)
        await metabolism.daydream()      # 每 10 tick
        await metabolism.quick_sleep()   # 每 50 tick
        await metabolism.full_sleep()    # 每会话结束
    """

    def __init__(
        self,
        working: WorkingMemory,
        stm: ShortTermMemory,
        ltm: LongTermMemory,
        core=None,  # CoreGraphMemory (可选)
    ):
        self.working = working
        self.stm = stm
        self.ltm = ltm
        self.core = core
        self.stats = MetabolismStats()

    def should_daydream(self, tick_count: int, interval: int = 10) -> bool:
        return tick_count % interval == 0

    def should_quick_sleep(self, tick_count: int, interval: int = 50) -> bool:
        return tick_count % interval == 0

    async def daydream(self) -> ConsolidationReport:
        """浅层睡眠 — 闲置期微合并。

        - 短期记忆中相邻且相似的记忆合并
        - 信任衰减
        """
        self.stats.daydream_count += 1
        self.stats.last_daydream = time.time()

        # STM 信任衰减
        report = await self.stm.consolidate()
        self.stats.total_merged += report.merged

        return report

    async def quick_sleep(self) -> ConsolidationReport:
        """快速睡眠 — 去重 + 信任衰减 + 层级提升。

        - 去重 (同实体+同情感+同时段 → 合并)
        - 信任评分衰减
        - Working → STM 提升
        - STM → LTM 提升
        """
        self.stats.quick_sleep_count += 1
        self.stats.last_quick = time.time()

        report = ConsolidationReport()

        # 1. Working → STM 提升
        for record in self.working.promote_candidates():
            await self.stm.store(record)
            report.promoted += 1

        # 2. STM → LTM 提升
        for record in self.stm.promote_candidates():
            await self.ltm.store(record)
            report.promoted += 1

        # 3. LTM 去重
        ltm_report = await self.ltm.consolidate()
        report.merged += ltm_report.merged

        self.stats.total_promoted += report.promoted
        self.stats.total_merged += report.merged

        return report

    async def full_sleep(self) -> ConsolidationReport:
        """深度睡眠 — 每会话结束触发。

        - 矛盾检测 (同实体相反情感 → 标记冲突)
        - 实体演化 (旧标签 superseded)
        - STM → LTM 提升
        - LTM → Core 提升
        - 索引重建
        """
        self.stats.full_sleep_count += 1
        self.stats.last_full = time.time()

        report = ConsolidationReport()

        # 1. 快速提升一次
        quick_report = await self.quick_sleep()
        report.promoted += quick_report.promoted

        # 2. LTM 矛盾检测
        conflicts = self.ltm.detect_contradictions()
        report.conflicts = len(conflicts)
        self.stats.total_conflicts += len(conflicts)

        # 3. LTM → Core 提升
        if self.core:
            for record in self.ltm.promote_candidates():
                await self.core.store(record)
                report.promoted += 1

        # 4. 遗忘: Working / STM / LTM 各执行淘汰
        report.archived += await self.working.forget()
        report.archived += await self.stm.forget()
        report.archived += await self.ltm.forget()

        self.stats.total_promoted += report.promoted
        self.stats.total_archived += report.archived

        return report
