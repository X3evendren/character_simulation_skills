"""意识层 — 注意力管理 + 完整自我叙事 + 预测加工。

注意力 + 预测: 纯数学，零额外 Token。
自我叙事: 低频 LLM 调用维护演化的自我认知故事。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ConsciousContent:
    """意识内容——一个进入工作空间的心理项目"""
    kind: str           # emotion / threat / defense / memory / response / perception
    content: str        # 内容描述
    salience: float = 0.0   # 显著性分数
    source: str = ""        # 来源
    timestamp: float = 0.0


def score_salience(
    candidates: list[ConsciousContent],
    drive_vector: dict[str, float] | None = None,
    prediction_error: float = 0.0,
) -> list[ConsciousContent]:
    """计算每个候选内容进入意识的显著性分数。

    显著性 = 情感强度(0.35) + 驱力相关性(0.25) + 预测误差(0.2) + 新颖性(0.2)

    纯数学计算，零 Token。
    """
    now = time.time()
    for item in candidates:
        item.timestamp = now

        # 情感强度: emotion 和 threat 类型天然高显著性
        emotion_score = 0.0
        if item.kind in ("emotion", "threat"):
            emotion_score = 0.7
        elif item.kind == "defense":
            emotion_score = 0.5
        elif item.kind == "response":
            emotion_score = 0.4

        # 驱力相关性: 检查内容是否与当前活跃驱力相关
        drive_score = 0.0
        if drive_vector:
            content_lower = item.content.lower()
            if "curiosity" in drive_vector and any(
                w in content_lower for w in ("问题", "探索", "发现", "学习")):
                drive_score = drive_vector["curiosity"]
            if "connection" in drive_vector and any(
                w in content_lower for w in ("用户", "关系", "理解", "感受")):
                drive_score = max(drive_score, drive_vector["connection"])
            if "helpfulness" in drive_vector and any(
                w in content_lower for w in ("任务", "帮助", "解决", "完成")):
                drive_score = max(drive_score, drive_vector["helpfulness"])

        # 新颖性: 越新的内容越显著（但此函数处理的都是当前 tick 的内容，差距不大）
        novelty_score = 0.5

        item.salience = (
            emotion_score * 0.35 +
            drive_score * 0.25 +
            prediction_error * 0.2 +
            novelty_score * 0.2
        )
        item.salience = max(0.0, min(1.0, item.salience))

    return candidates


def update_workspace(
    candidates: list[ConsciousContent],
    capacity: int = 4,
    threshold: float = 0.3,
) -> list[ConsciousContent]:
    """有限工作空间: 只保留显著性最高的 N 项。

    类似 Global Workspace Theory (GWT) 的选择性广播。
    低于阈值的项目被"抑制"——不进入意识。
    """
    valid = [c for c in candidates if c.salience >= threshold]
    valid.sort(key=lambda c: c.salience, reverse=True)
    return valid[:capacity]
