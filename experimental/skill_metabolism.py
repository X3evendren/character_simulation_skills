"""Skill Metabolism — Skills 激活追踪、淘汰标记、合并建议。

每个 Skill 被追踪: 激活次数、最后使用时间、平均质量、token成本、输出重叠度。
自动检测: 长期未激活 → FLAGGED, 输出高度重叠 → MERGE_CANDIDATE,
质量差 → FLAGGED, token 过高 → OPTIMIZE_CANDIDATE。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SkillTracker:
    """单个 Skill 的运行时追踪数据。"""
    skill_name: str
    layer: int
    activation_count: int = 0
    last_activated: float = 0.0
    total_tokens: int = 0
    parse_success_count: int = 0
    parse_fail_count: int = 0
    quality_scores: list[float] = field(default_factory=list)  # 最近 N 次质量分
    output_overlap_with: dict[str, float] = field(default_factory=dict)  # {skill_name: overlap_ratio}
    status: str = "active"  # active / flagged / merge_candidate / optimize_candidate / archived

    @property
    def avg_token_cost(self) -> float:
        if self.activation_count == 0:
            return 0
        return self.total_tokens / self.activation_count

    @property
    def avg_quality_score(self) -> float:
        if not self.quality_scores:
            return 0.5
        return sum(self.quality_scores) / len(self.quality_scores)

    @property
    def parse_success_rate(self) -> float:
        total = self.parse_success_count + self.parse_fail_count
        if total == 0:
            return 1.0
        return self.parse_success_count / total

    def record_activation(self, tokens: int, parse_success: bool, quality: float = 0.5):
        self.activation_count += 1
        self.last_activated = time.time()
        self.total_tokens += tokens
        if parse_success:
            self.parse_success_count += 1
        else:
            self.parse_fail_count += 1
        self.quality_scores.append(quality)
        if len(self.quality_scores) > 50:
            self.quality_scores = self.quality_scores[-50:]

    def days_since_activation(self) -> float:
        if self.last_activated == 0:
            return 999
        return (time.time() - self.last_activated) / 86400.0

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "layer": self.layer,
            "activation_count": self.activation_count,
            "last_activated": self.last_activated,
            "avg_token_cost": self.avg_token_cost,
            "avg_quality_score": round(self.avg_quality_score, 3),
            "parse_success_rate": round(self.parse_success_rate, 3),
            "output_overlap_with": self.output_overlap_with,
            "status": self.status,
        }


class SkillMetabolism:
    """管理 Skills 的生命周期。

    淘汰策略:
    - 30天未激活 → FLAGGED
    - avg_quality < 0.3 且 activation_count >= 10 → FLAGGED
    - output_overlap > 0.7 → MERGE_CANDIDATE
    - token_cost > 2×同类平均且质量不显著更高 → OPTIMIZE_CANDIDATE
    """

    def __init__(self):
        self.trackers: dict[str, SkillTracker] = {}

    def register(self, skill_name: str, layer: int):
        if skill_name not in self.trackers:
            self.trackers[skill_name] = SkillTracker(skill_name=skill_name, layer=layer)

    def record(self, skill_name: str, tokens: int, parse_success: bool, quality: float = 0.5):
        if skill_name not in self.trackers:
            self.register(skill_name, layer=-1)
        self.trackers[skill_name].record_activation(tokens, parse_success, quality)

    def update_overlap(self, skill_a: str, skill_b: str, overlap: float):
        """记录两个 Skill 的输出重叠度。"""
        if skill_a in self.trackers:
            self.trackers[skill_a].output_overlap_with[skill_b] = overlap
        if skill_b in self.trackers:
            self.trackers[skill_b].output_overlap_with[skill_a] = overlap

    def run_metabolism(self) -> dict:
        """运行一次代谢周期。返回变更报告。"""
        report = {"flagged": [], "merge_candidates": [], "optimize_candidates": [],
                   "archived": []}
        layer_stats: dict[int, dict] = {}  # {layer: {total_tokens, count, active_count}}

        # 收集各层统计
        for t in self.trackers.values():
            if t.layer not in layer_stats:
                layer_stats[t.layer] = {"total_tokens": 0, "count": 0, "active_count": 0}
            ls = layer_stats[t.layer]
            ls["total_tokens"] += t.avg_token_cost
            ls["count"] += 1
            if t.status == "active":
                ls["active_count"] += 1

        for t in self.trackers.values():
            # 30天未激活
            if t.days_since_activation() > 30:
                t.status = "flagged"
                report["flagged"].append(f"{t.skill_name}: 30天未激活")

            # 低质量
            elif t.activation_count >= 10 and t.avg_quality_score < 0.3:
                t.status = "flagged"
                report["flagged"].append(f"{t.skill_name}: 质量过低({t.avg_quality_score:.2f})")

            # 输出重叠
            for other, overlap in t.output_overlap_with.items():
                if overlap > 0.7 and t.status == "active":
                    t.status = "merge_candidate"
                    report["merge_candidates"].append(f"{t.skill_name} ↔ {other}: 重叠{overlap:.0%}")

            # Token 过高
            layer_avg = layer_stats.get(t.layer, {})
            if layer_avg.get("count", 0) > 1 and t.avg_token_cost > 0:
                layer_mean_token = layer_avg["total_tokens"] / layer_avg["count"]
                if t.avg_token_cost > layer_mean_token * 2 and t.avg_quality_score <= 0.6:
                    t.status = "optimize_candidate"
                    report["optimize_candidates"].append(
                        f"{t.skill_name}: {t.avg_token_cost:.0f} tokens vs 层平均{layer_mean_token:.0f}"
                    )

        return report

    def get_noise_report(self) -> dict:
        """Skills 噪音报告: 冗余和低质量 skill 占比。"""
        total = len(self.trackers)
        if total == 0:
            return {"skill_noise_ratio": 0.0, "total_skills": 0}
        flagged = sum(1 for t in self.trackers.values() if t.status == "flagged")
        merge = sum(1 for t in self.trackers.values() if t.status == "merge_candidate")
        optimize = sum(1 for t in self.trackers.values() if t.status == "optimize_candidate")
        noisy = flagged + merge + optimize
        return {
            "skill_noise_ratio": round(noisy / total, 2),
            "total_skills": total,
            "flagged": flagged,
            "merge_candidates": merge,
            "optimize_candidates": optimize,
        }

    def to_dict(self) -> dict:
        return {"trackers": {k: v.to_dict() for k, v in self.trackers.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> "SkillMetabolism":
        sm = cls()
        for name, d in data.get("trackers", {}).items():
            t = SkillTracker(
                skill_name=d["skill_name"], layer=d.get("layer", -1),
                activation_count=d.get("activation_count", 0),
                last_activated=d.get("last_activated", 0),
                total_tokens=d.get("total_tokens", 0) if "total_tokens" in d else d.get("avg_token_cost", 0) * d.get("activation_count", 0),
                parse_success_count=d.get("parse_success_count", 0),
                parse_fail_count=d.get("parse_fail_count", 0),
                output_overlap_with=d.get("output_overlap_with", {}),
                status=d.get("status", "active"),
            )
            sm.trackers[name] = t
        return sm
