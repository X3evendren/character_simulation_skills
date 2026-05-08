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

    async def consolidate(self, orchestrator, provider, character_state: dict) -> dict:
        """执行一次离线巩固：重播近期显著记忆，更新 Blackboard 长期状态。

        注意: 当前走完整 process_event() pipeline。
        计划优化: 只跑 L0+L4（不跑 L5 回应生成）。
        character_state 必须传入角色真实档案。
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

            result = await orchestrator.process_event(provider, character_state, event)

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

        # 从工作空间学习过程规则（当fear/abandonment模式重复出现时）
        ws = self.bb.read(["conscious_workspace"]).get("conscious_workspace", [])
        ws_text = " ".join(str(item.get("content", "")) for item in ws)
        if "fear" in ws_text or "没有回复" in ws_text:
            rules = self.bb.read(["procedural_rules"]).get("procedural_rules", [])
            rules.append({
                "t": now,
                "trigger": "对方沉默",
                "prediction": "我会被抛弃",
                "defense": "冷淡试探",
                "response_style": "短句、否认需要",
                "weight": 0.6,
            })
            self.bb.write("procedural_rules", rules[-20:])

        # 写入冻结快照
        self.bb.write("frozen_snapshot", self.build_frozen_snapshot())

        return {
            "consolidated": True,
            "events_replayed": consolidated,
            "consolidation_num": self.state.consolidation_count,
        }

    def build_frozen_snapshot(self) -> dict:
        current = self.bb.read([
            "conscious_workspace",
            "self_perception",
            "dominant_emotion",
            "pad",
            "active_defense",
            "schema_trajectory",
        ])
        return {
            "t": time.time(),
            "workspace": current.get("conscious_workspace", []),
            "self_perception": current.get("self_perception", ""),
            "dominant_emotion": current.get("dominant_emotion", "neutral"),
            "pad": current.get("pad", {}),
            "active_defense": current.get("active_defense", {}),
            "schema_trajectory": current.get("schema_trajectory", []),
        }

    def extract_divergence_rule(self) -> dict:
        inner = self.bb.read(["inner_experience"]).get("inner_experience", {})
        items = inner.get("items", [])
        divergences = [
            item for item in items
            if item.get("kind") == "inner_outer_divergence"
        ]
        if not divergences:
            return {}
        latest = divergences[-1]
        rule = {
            "t": time.time(),
            "trigger": "高强度未表达需求",
            "prediction": latest.get("inner", {}).get("content", ""),
            "defense": latest.get("mechanism", "masking"),
            "response_style": latest.get("outer", {}).get("content", ""),
            "weight": min(1.0, latest.get("intensity", 0.5)),
        }
        rules = self.bb.read(["procedural_rules"]).get("procedural_rules", [])
        rules.append(rule)
        self.bb.write("procedural_rules", rules[-20:])
        return rule

    def stats(self) -> dict:
        return {
            "consolidations": self.state.consolidation_count,
            "memories_replayed": self.state.memories_replayed,
            "significant_events": self.state.significant_event_count,
            "last_consolidation": self.state.last_consolidation,
        }
