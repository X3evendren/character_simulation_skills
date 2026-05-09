"""Curator Scheduler — 技能审查自动调度器。

包装 SkillCurator + CronScheduler，按 cron 表达式自动触发技能审查。
连续 3 次 "degraded/redundant" 后自动归档（可配置人工确认）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .skill_curator import SkillCurator, CuratorReview


@dataclass
class CuratorScheduler:
    """自动审查调度器。

    用法:
        scheduler = CuratorScheduler(curator, metabolism)
        scheduler.schedule("0 3 * * *")  # 每天凌晨 3 点审查
        await scheduler.tick()            # 在主循环中调用
    """

    curator: SkillCurator
    metabolism: object  # SkillMetabolism 实例
    cron_expr: str = "0 3 * * *"
    interval_seconds: int = 86400  # 默认每天
    auto_confirm: bool = False     # True = 自动归档，False = 仅标记
    max_auto_archive: int = 3      # 单次自动归档上限
    pending_archivals: list[dict] = field(default_factory=list)
    _last_run: float = 0.0
    _run_count: int = 0

    def schedule(self, cron_expr: str) -> None:
        """设置审查调度。支持简化的 cron 别名。"""
        self.cron_expr = cron_expr
        secs = _parse_cron_seconds(cron_expr)
        self.interval_seconds = secs

    def should_run(self) -> bool:
        """是否应该触发审查？"""
        if self._run_count == 0:
            return True  # 启动后立即运行一次
        return (time.time() - self._last_run) >= self.interval_seconds

    def run_review(self, trackers: dict[str, object]) -> list[CuratorReview]:
        """运行审查周期——对所有非 pinned 技能进行审查。"""
        self._last_run = time.time()
        self._run_count += 1
        reviews: list[CuratorReview] = []

        for name, tracker in trackers.items():
            if getattr(tracker, "pinned", False):
                continue
            if getattr(tracker, "generated_by", "human") == "human":
                # 内建技能仅检查质量趋势，不自动归档
                review = self.curator.review(name, tracker)
                reviews.append(review)
                continue

            review = self.curator.review(name, tracker)
            reviews.append(review)

            if review.health == "should_archive":
                self._handle_archival(name, review)

        self.curator._last_review_time = time.time()
        return reviews

    def _handle_archival(self, skill_name: str, review: CuratorReview) -> None:
        """处理归档决策。"""
        if self.auto_confirm and len(self.pending_archivals) < self.max_auto_archive:
            if hasattr(self.metabolism, "commit_archive"):
                self.metabolism.commit_archive(skill_name)
            review.suggestions.append("已自动归档")
        else:
            self.pending_archivals.append({
                "skill_name": skill_name,
                "consecutive_degraded": review.consecutive_degraded,
                "reviewed_at": review.reviewed_at,
            })

    def confirm_archival(self, skill_name: str) -> bool:
        """人工确认归档。"""
        if hasattr(self.metabolism, "commit_archive"):
            self.metabolism.commit_archive(skill_name)
        self.pending_archivals = [
            p for p in self.pending_archivals if p["skill_name"] != skill_name
        ]
        return True

    def reject_archival(self, skill_name: str) -> bool:
        """拒绝归档——将技能标记为 pinned 防止再次归档。"""
        self.pending_archivals = [
            p for p in self.pending_archivals if p["skill_name"] != skill_name
        ]
        if hasattr(self.metabolism, "trackers") and skill_name in self.metabolism.trackers:
            self.metabolism.trackers[skill_name].pinned = True
        return True

    def status(self) -> dict:
        return {
            "run_count": self._run_count,
            "last_run": self._last_run,
            "interval_seconds": self.interval_seconds,
            "pending_archivals": len(self.pending_archivals),
            "auto_confirm": self.auto_confirm,
        }

    def to_dict(self) -> dict:
        return {
            "cron_expr": self.cron_expr,
            "interval_seconds": self.interval_seconds,
            "auto_confirm": self.auto_confirm,
            "last_run": self._last_run,
            "run_count": self._run_count,
            "pending_archivals": self.pending_archivals,
        }


def _parse_cron_seconds(expr: str) -> int:
    """将 cron 表达式转换为秒。支持简化格式。"""
    expr = expr.strip()
    if expr == "hourly":
        return 3600
    if expr == "daily" or expr == "daily_9am":
        return 86400
    if expr.startswith("*/"):
        try:
            return int(expr[2:])
        except ValueError:
            pass
    try:
        return int(expr)
    except ValueError:
        pass
    # 简单 5-field cron: 解析分钟和小时
    parts = expr.split()
    if len(parts) >= 2:
        try:
            minute = int(parts[0]) if parts[0] != "*" else 0
            hour = int(parts[1]) if parts[1] != "*" else 0
            now = time.localtime()
            target = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hour, minute, 0,
                                  now.tm_wday, now.tm_yday, now.tm_isdst))
            if target <= time.time():
                target += 86400
            return int(target - time.time())
        except (ValueError, OverflowError):
            pass
    return 86400  # 默认每天
