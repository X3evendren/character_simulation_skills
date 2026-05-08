"""TocaRunner — TOCA 时间偏移实例调度器。

管理 N 个管道实例在时间偏移上的并发运行。
每个实例 = process_event() 的一次调用。
实例读取 Blackboard 最新状态 + 自己的感知窗口 → 处理后写回 Blackboard。
"""
from __future__ import annotations

import asyncio
import time
import math
from dataclasses import dataclass, field
from typing import Any

from .blackboard import Blackboard
from .perception_stream import PerceptionStream
from .consciousness import ConsciousnessLayer
from .thalamic_gate import ThalamicGate
from .offline_consolidation import OfflineConsolidation
from .wm_ltm_bridge import WmLtmBridge
from .self_model import SelfModel
from .procedural_memory import ProceduralMemoryStore


@dataclass
class InstanceMeta:
    """管道实例的运行时元数据"""
    id: int
    started_at: float
    completed_at: float = 0.0
    tokens_used: int = 0
    writes_succeeded: int = 0
    writes_conflicted: int = 0
    status: str = "running"  # running | completed | conflicted | error


@dataclass
class TocaConfig:
    """TOCA 调度配置"""
    pipeline_time_s: float = 3.0       # 单次管道估算耗时（秒）
    instance_count: int = 3            # 并发实例数
    window_s: float = 10.0             # 每个实例的感知窗口（秒）

    @property
    def interval(self) -> float:
        """实例启动间隔。间隔之和 ≈ pipeline_time → 体感连续。"""
        return self.pipeline_time_s / self.instance_count


class TocaRunner:
    """TOCA 时间偏移调度器。

    用法:
        bb = Blackboard()
        ps = PerceptionStream()
        config = TocaConfig(pipeline_time_s=3.0, instance_count=3)

        runner = TocaRunner(bb, ps, orchestrator, provider, character_state, config)
        await runner.start()  # 启动连续流
        # ... 外部向 ps 输入感知 ...
        await asyncio.sleep(30)
        await runner.stop()   # 停止
    """

    def __init__(self, blackboard: Blackboard, perception_stream: PerceptionStream,
                 orchestrator, provider, character_state: dict,
                 config: TocaConfig | None = None):
        self.bb = blackboard
        self.ps = perception_stream
        self.orchestrator = orchestrator
        self.provider = provider
        self.character_state = character_state
        self.config = config or TocaConfig()
        self.behavior_stream = None  # 可选：由外部注入

        self._instances: list[InstanceMeta] = []
        self._running = False
        self._next_id = 1
        self._tasks: list[asyncio.Task] = []

        # 意识层: GWT + HOT + 预测加工
        self.consciousness = ConsciousnessLayer(blackboard)

        # 丘脑门控: 感知过滤
        self.thalamic_gate = ThalamicGate()

        # 离线巩固: Nudge Engine + 记忆重播
        self.offline_consolidation = OfflineConsolidation(
            blackboard, orchestrator.episodic_store if orchestrator else None)

        # WM-LTM 桥接
        self.wm_ltm_bridge = WmLtmBridge(
            orchestrator.episodic_store if orchestrator else None)

        # 自我模型
        self.self_model = SelfModel()

        # 过程记忆
        self.procedural_memory = ProceduralMemoryStore()

        # 记录最后一次输入时间
        self._last_input_time = time.time()

        # 初始化 Blackboard 基线状态
        if "pad" not in self.bb:
            self.bb.write("pad", {"pleasure": 0.0, "arousal": 0.3, "dominance": 0.0})

    async def start(self):
        """启动连续流调度。"""
        self._running = True
        self._schedule_loop = asyncio.create_task(self._scheduler())
        self._consolidation_loop = asyncio.create_task(self._consolidation_monitor())

    async def stop(self):
        """停止调度，等待所有运行中的实例完成。"""
        self._running = False
        if self._schedule_loop:
            self._schedule_loop.cancel()
        consolidation_loop = getattr(self, '_consolidation_loop', None)
        if consolidation_loop:
            self._consolidation_loop.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _consolidation_monitor(self):
        """后台监控：定期检查是否需要离线巩固。"""
        while self._running:
            await asyncio.sleep(5)  # 每5秒检查一次
            if self.offline_consolidation.should_consolidate(self._last_input_time):
                await self.offline_consolidation.consolidate(
                    self.orchestrator, self.provider, self.character_state)

    async def _scheduler(self):
        """主调度循环：按时间间隔启动管道实例。"""
        interval = self.config.interval
        while self._running:
            task = asyncio.create_task(self._run_instance())
            self._tasks.append(task)
            # 清理已完成的 task
            self._tasks = [t for t in self._tasks if not t.done()]
            await asyncio.sleep(interval)

    async def _run_instance(self):
        """运行一次管道实例。
        每次实例读取 Blackboard 最新状态 + 感知窗口 → 管道分析 → 写回。"""
        instance_id = self._next_id
        self._next_id += 1

        meta = InstanceMeta(id=instance_id, started_at=time.time())
        self._instances.append(meta)

        try:
            # 1. 读取 Blackboard 最新状态 + 感知窗口
            snap = self.bb.read_with_versions()
            perception_window = self.ps.get_window(self.config.window_s)

            # 2. 丘脑门控: 过滤低显著性感知
            if perception_window:
                latest = perception_window[-1]
                gate_result = self.thalamic_gate.evaluate(latest)
                if not gate_result["should_process"]:
                    meta.status = "gated"
                    return
                # 门控触发后消费缓冲区，合并累积感知到当前窗口
                buffered = self.thalamic_gate.flush()
                if buffered:
                    seen = set()
                    merged = []
                    for item in buffered + perception_window:
                        key = (item.get("t"), item.get("modality"), item.get("content"))
                        if key not in seen:
                            seen.add(key)
                            merged.append(item)
                    perception_window = merged

            # 3. 预测加工: 层次化预测下一帧状态
            self.consciousness.predict_next()

            # 4. WM-LTM 桥接: 检索相关历史记忆
            retrieved_memories = self.wm_ltm_bridge.check_and_retrieve(
                perception_window,
                current_emotion=snap.get("dominant_emotion", (None,))[0] or "",
            )
            memory_context = self.wm_ltm_bridge.format_for_context(retrieved_memories)

            # 4.5. 过程记忆检索
            perception_text = " ".join(p.get("content", "") for p in perception_window)
            procedural_matches = self.procedural_memory.retrieve(perception_text)
            procedural_context = ""
            if procedural_matches:
                lines = ["[习得模式]"]
                for rule in procedural_matches[:2]:
                    lines.append(
                        f"- 触发:{rule['trigger']} 预期:{rule['prediction']} "
                        f"防御:{rule['defense']} 表达:{rule['response_style']}"
                    )
                procedural_context = "\n".join(lines)

            # 5. 构建事件（感知 + 心理状态 + 记忆上下文）
            event = self._build_event(perception_window, snap,
                                     memory_context + "\n" + procedural_context)
            if event is None:
                meta.status = "idle"
                return
            self.bb.write("last_continuous_event", event, instance_id)

            # 4. 注入 Blackboard 累积状态到 character_state
            cs = self._build_continuous_state(snap)

            # 5. 运行管道（使用持有实例）
            result = await self.orchestrator.process_event(self.provider, cs, event)
            meta.tokens_used = result.total_tokens

            # 6. 写回 Blackboard（实时版本号）
            self._write_back(result, instance_id, snap)

            # 6.5. 行为流发布
            response = self.get_latest_response()
            if self.behavior_stream is not None and response and response.get("text"):
                last_speech = self.behavior_stream.get_last_speech()
                if not last_speech or last_speech.get("content") != response["text"]:
                    self.behavior_stream.emit("speech", response["text"],
                                            response.get("confidence", 0.8))

            # 7. 意识层处理
            self.consciousness.compute_prediction_error()
            broadcast = self.consciousness.filter_broadcast()

            # 7.5. 构建工作空间 + 更新自我模型
            candidates = self.consciousness.build_workspace_candidates()
            workspace = self.consciousness.update_workspace(candidates)
            self_model_state = self.self_model.update(workspace)
            self.bb.write("self_model", self_model_state, instance_id)
            self.consciousness.self_perceive()

            # 8. Nudge Engine: 记录显著事件
            if event.get("significance", 0) >= 0.4:
                self.offline_consolidation.on_significant_event(event["significance"])

            meta.status = "completed"
            meta.completed_at = time.time()

        except Exception as e:
            meta.status = "error"
            self._instances[-1] = meta

    def _build_continuous_state(self, snap: dict) -> dict:
        """从 Blackboard 快照构建当前角色状态。
        合并基线人格与累积的心理状态——这是连续性的关键。"""
        cs = dict(self.character_state)

        # 注入累积情感状态
        pad = snap.get("pad", (None,))[0]
        if pad:
            cs["emotion_decay"] = {
                "fast": {"pleasure": pad.get("pleasure", 0), "arousal": pad.get("arousal", 0.5), "dominance": pad.get("dominance", 0)},
                "slow": {"pleasure": pad.get("pleasure", 0) * 0.8, "arousal": pad.get("arousal", 0.5) * 0.8, "dominance": pad.get("dominance", 0) * 0.8},
            }
            cs["current_emotion"] = snap.get("dominant_emotion", (None,))[0] or "neutral"

        # 注入防御状态
        defense = snap.get("active_defense", (None,))[0]
        if defense and isinstance(defense, dict) and defense.get("name"):
            current_defenses = cs.get("personality", {}).get("defense_style", [])
            if defense["name"] not in current_defenses:
                cs.setdefault("current_defense", defense)

        # 注入 PTSD 触发状态
        triggered = snap.get("ptsd_triggered", (None,))[0]
        if triggered is not None:
            cs["current_ptsd_triggered"] = triggered

        return cs

    def _build_event(self, perception_window: list[dict], snap: dict | None = None,
                     memory_context: str = "") -> dict | None:
        """从感知窗口 + 当前心理状态 + 记忆上下文构建管道事件。"""
        if not perception_window:
            return None

        descriptions = []
        tags = set()
        for p in perception_window:
            desc = p["content"]
            if p.get("source"):
                desc = f"[{p['source']}] {desc}"
            descriptions.append(desc)
            tags.add(p.get("modality", ""))

        context = ""
        if snap:
            dom = snap.get("dominant_emotion", (None,))[0]
            if dom:
                context = f"（当前情绪: {dom}）"

        desc = context + " " + " ".join(descriptions[-6:])
        if memory_context:
            desc = memory_context + "\n" + desc

        return {
            "description": desc,
            "type": "continuous",
            "participants": [],
            "significance": 0.4,
            "tags": list(tags),
            "_toca_instance": True,
        }

    def _write_back(self, result, instance_id: int, expected_versions: dict | None = None) -> tuple[int, int]:
        """将管道产出写回 Blackboard。

        使用实例启动时的快照版本做乐观锁检查。如果未提供 expected_versions，
        则退回到实时读取版本（非连续模式下兼容旧调用）。"""
        writes = 0
        conflicts = 0

        l1 = result.layer_results.get(1, [])
        l2 = result.layer_results.get(2, [])
        l5 = result.layer_results.get(5, [])

        versions = expected_versions or self.bb.read_with_versions()

        # L1: 情感
        for sr in l1:
            if sr.skill_name == "plutchik_emotion" and sr.success:
                internal = sr.output.get("internal", {})
                pad = {
                    "pleasure": internal.get("pleasantness", 0.0),
                    "arousal": internal.get("intensity", 0.5),
                    "dominance": 0.0,
                }
                ev = versions.get("pad", (None, 0))[1]
                if self.bb.try_write("pad", pad, ev, instance_id):
                    writes += 1
                else:
                    conflicts += 1
                ev2 = versions.get("dominant_emotion", (None, 0))[1]
                if self.bb.try_write("dominant_emotion", internal.get("dominant", "neutral"),
                                     ev2, instance_id):
                    writes += 1
                else:
                    conflicts += 1
                break

        # L1: PTSD
        for sr in l1:
            if sr.skill_name == "ptsd_trigger_check" and sr.success:
                ev = versions.get("ptsd_triggered", (None, 0))[1]
                if self.bb.try_write("ptsd_triggered", sr.output.get("triggered", False),
                                     ev, instance_id):
                    writes += 1
                else:
                    conflicts += 1
                break

        # L2: 防御
        for sr in l2:
            if sr.skill_name == "defense_mechanism_analysis" and sr.success:
                ev = versions.get("active_defense", (None, 0))[1]
                if self.bb.try_write("active_defense", sr.output.get("activated_defense", {}),
                                     ev, instance_id):
                    writes += 1
                else:
                    conflicts += 1
                break

        # L5: 回应
        for sr in l5:
            if sr.skill_name == "response_generator" and sr.success:
                rt = sr.output.get("response_text", "")
                if rt:
                    ev = versions.get("pending_response", (None, 0))[1]
                    if self.bb.try_write("pending_response",
                                         {"text": rt, "confidence": 0.8, "t": time.time()},
                                         ev, instance_id):
                        writes += 1
                    else:
                        conflicts += 1
                break

        # 更新实例元数据
        for i, m in enumerate(self._instances):
            if m.id == instance_id:
                self._instances[i].writes_succeeded = writes
                self._instances[i].writes_conflicted = conflicts
                break
        return writes, conflicts

    # ═══ 状态查询 ═══

    def stats(self) -> dict:
        """获取调度统计。"""
        completed = [m for m in self._instances if m.status == "completed"]
        return {
            "total_instances": len(self._instances),
            "completed": len(completed),
            "running": sum(1 for m in self._instances if m.status == "running"),
            "errors": sum(1 for m in self._instances if m.status == "error"),
            "total_tokens": sum(m.tokens_used for m in self._instances),
            "avg_pipeline_time": (
                sum(m.completed_at - m.started_at for m in completed) / len(completed)
                if completed else 0
            ),
            "write_success_rate": (
                sum(m.writes_succeeded for m in completed) /
                max(sum(m.writes_succeeded + m.writes_conflicted for m in completed), 1)
                if completed else 0
            ),
        }

    def get_latest_response(self) -> dict | None:
        """获取最新待输出回应。"""
        resp = self.bb.read(["pending_response"]).get("pending_response")
        return resp
