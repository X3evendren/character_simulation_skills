"""Offline Consolidation — 离线巩固模块。

借鉴 Hermes Nudge Engine + 海马回放机制。
在无外部输入时自动触发，重播近期显著记忆，巩固到 Blackboard 长期状态。
"""
from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass, field


@dataclass
class NudgeState:
    """Nudge Engine 状态"""
    significant_event_count: int = 0     # 显著事件计数
    last_consolidation: float = 0.0       # 上次巩固时间
    consolidation_count: int = 0          # 总巩固次数
    memories_replayed: int = 0            # 重播的记忆数量

    # Nudge 阈值
    event_threshold: int = 5              # N 次显著事件后触发
    idle_threshold: float = 5.0           # 无输入 N 秒后触发
    cooldown: float = 30.0               # 两次巩固最小间隔


class OfflineConsolidation:
    """离线巩固：Nudge Engine + 记忆重播。

    用法:
        oc = OfflineConsolidation(blackboard, episodic_store)
        # ... 在线处理 ...
        if oc.should_consolidate(last_input_time):
            await oc.consolidate(orchestrator, provider)
    """

    def __init__(self, blackboard, episodic_store):
        self.bb = blackboard
        self.episodic_store = episodic_store
        self.state = NudgeState()

    def on_significant_event(self, significance: float = 0.5):
        """当发生显著事件时调用。Nudge Engine 计数。"""
        if significance >= 0.4:
            self.state.significant_event_count += 1

    def should_consolidate(self, last_input_time: float | None = None) -> bool:
        """是否应该触发离线巩固？"""
        now = time.time()

        # 冷却期内不触发
        if now - self.state.last_consolidation < self.state.cooldown:
            return False

        # 条件1: 累积了足够多的显著事件
        if self.state.significant_event_count >= self.state.event_threshold:
            return True

        # 条件2: 无外部输入超过阈值
        if last_input_time and (now - last_input_time) > self.state.idle_threshold:
            return True

        return False

    async def consolidate(self, orchestrator, provider, character_state: dict = None) -> dict:
        """执行一次离线巩固：重播近期显著记忆，更新 Blackboard 长期状态。

        注意: 当前走完整 process_event() pipeline。
        计划优化: 只跑 L0+L4（不跑 L5 回应生成）。
        character_state 应传入角色真实档案，未提供时使用 fallback。
        """
        now = time.time()
        self.state.last_consolidation = now
        self.state.consolidation_count += 1

        # 1. 获取近期高显著性记忆（重播素材）
        significant = self.episodic_store.get_significant(threshold=0.5)
        recent = self.episodic_store.get_recent(5)
        replay_events = significant[:3] + recent[:3]

        if not replay_events:
            return {"consolidated": False, "reason": "no memories to replay"}

        # 2. 重播：对每条记忆运行轻量分析
        consolidated = 0
        for memory in replay_events[:5]:
            event = {
                "description": f"[记忆重播] {memory.description[:200]}",
                "type": memory.event_type or "recall",
                "significance": memory.significance,
                "tags": memory.tags + ["consolidation", "replay"],
            }

            cs = character_state if character_state else self._build_cs_for_consolidation()
            result = await orchestrator.process_event(provider, cs, event)

            # 提取反思结果
            l4 = result.layer_results.get(4, [])
            for sr in l4:
                if sr.skill_name == "gross_emotion_regulation" and sr.success:
                    self.bb.write("reflection", sr.output.get("regulation_insight", ""))
                if sr.skill_name == "kohlberg_moral_reasoning" and sr.success:
                    self.bb.write("moral_stance", {
                        "stage": sr.output.get("stage_used", 3),
                        "conflict": sr.output.get("moral_conflict", ""),
                    })

            consolidated += 1

        # 3. 更新图式/ACE长期轨迹
        schema_changes = self.bb.read(["schema_trajectory"]).get("schema_trajectory", [])
        if not schema_changes:
            schema_changes = []
        schema_changes.append({
            "t": now,
            "trigger": f"auto-consolidation #{self.state.consolidation_count}",
            "events_replayed": consolidated,
        })
        self.bb.write("schema_trajectory", schema_changes[-5:])  # 只保留最近5条

        # 4. 重置计数器
        self.state.significant_event_count = 0
        self.state.memories_replayed += consolidated

        return {
            "consolidated": True,
            "events_replayed": consolidated,
            "consolidation_num": self.state.consolidation_count,
        }

    def _build_cs_for_consolidation(self) -> dict:
        """构建离线巩固用的角色状态。"""
        state = self.bb.read(["pad", "dominant_emotion", "active_defense",
                               "self_perception", "schema_trajectory"])
        return {
            "name": "角色",
            "personality": {
                "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                "agreeableness": 0.5, "neuroticism": 0.5,
                "attachment_style": "secure", "defense_style": [],
                "cognitive_biases": [], "moral_stage": 3,
            },
            "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
            "ideal_world": {},
            "motivation": {"current_goal": ""},
            "emotion_decay": {
                "fast": {"pleasure": state.get("pad", {}).get("pleasure", 0),
                         "arousal": state.get("pad", {}).get("arousal", 0.5)},
                "slow": {},
            },
        }

    def stats(self) -> dict:
        return {
            "consolidations": self.state.consolidation_count,
            "memories_replayed": self.state.memories_replayed,
            "significant_events": self.state.significant_event_count,
            "last_consolidation": self.state.last_consolidation,
        }
