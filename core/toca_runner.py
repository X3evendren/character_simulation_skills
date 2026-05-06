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

        self._instances: list[InstanceMeta] = []
        self._running = False
        self._next_id = 1
        self._tasks: list[asyncio.Task] = []

        # 初始化 Blackboard 基线状态
        if "pad" not in self.bb:
            self.bb.write("pad", {"pleasure": 0.0, "arousal": 0.3, "dominance": 0.0})

    async def start(self):
        """启动连续流调度。"""
        self._running = True
        self._schedule_loop = asyncio.create_task(self._scheduler())

    async def stop(self):
        """停止调度，等待所有运行中的实例完成。"""
        self._running = False
        if self._schedule_loop:
            self._schedule_loop.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

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
        """运行一次管道实例。"""
        instance_id = self._next_id
        self._next_id += 1

        meta = InstanceMeta(id=instance_id, started_at=time.time())
        self._instances.append(meta)

        try:
            # 1. 读取 Blackboard 最新状态 + 感知窗口
            snap = self.bb.read_with_versions()
            perception_window = self.ps.get_window(self.config.window_s)

            # 2. 构建事件（从感知窗口 + 当前心理状态）
            event = self._build_event(perception_window, snap)
            if event is None:
                meta.status = "idle"
                return

            # 3. 将 Blackboard 上的连续心理状态注入 character_state
            cs = dict(self.character_state)
            self._inject_blackboard_state(cs, snap)

            # 4. 运行管道
            from .orchestrator import get_orchestrator
            import character_simulation_skills.core.orchestrator as orch
            orch._orchestrator = None
            orch_or = get_orchestrator(anti_alignment_enabled=True)

            result = await orch_or.process_event(self.provider, cs, event)
            meta.tokens_used = result.total_tokens

            # 5. 写入 Blackboard（实时读版本号，不是用管道开始时的快照）
            self._write_back(result, instance_id)
            meta.status = "completed"
            meta.completed_at = time.time()

        except Exception as e:
            meta.status = "error"
            self._instances[-1] = meta
            raise

    def _inject_blackboard_state(self, cs: dict, snap: dict):
        """将 Blackboard 上的连续心理状态注入 character_state。
        这是连续性的关键：每次管道调用看到的不是初始角色，而是'此刻'的角色。"""
        state_map = {
            "pad": "emotion_decay",
            "active_defense": "current_defense",
            "dominant_emotion": "current_emotion",
        }
        for bb_key, cs_key in state_map.items():
            if bb_key in snap and snap[bb_key][0] is not None:
                cs[cs_key] = snap[bb_key][0]

    def _build_event(self, perception_window: list[dict], snap: dict | None = None) -> dict | None:
        """从感知窗口 + 当前心理状态构建管道事件。"""
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

        # 注入当前心理状态作为事件上下文
        context = ""
        if snap:
            dom = snap.get("dominant_emotion", (None,))[0]
            if dom:
                context = f"（当前角色情绪基调: {dom}）"

        return {
            "description": context + " " + " ".join(descriptions[-6:]),
            "type": "continuous",
            "participants": [],
            "significance": 0.4,
            "tags": list(tags),
            "_toca_instance": True,
        }

    def _write_back(self, result, instance_id: int):
        """将管道产出写回 Blackboard。
        注意：版本号在写入时实时读取（不是管道开始时的快照）。"""
        writes = 0
        conflicts = 0

        l1 = result.layer_results.get(1, [])
        l2 = result.layer_results.get(2, [])
        l5 = result.layer_results.get(5, [])

        # 实时读版本号（不是管道开始时的快照）
        now_versions = self.bb.read_with_versions()

        # L1: 情感
        for sr in l1:
            if sr.skill_name == "plutchik_emotion" and sr.success:
                internal = sr.output.get("internal", {})
                pad = {
                    "pleasure": internal.get("pleasantness", 0.0),
                    "arousal": internal.get("intensity", 0.5),
                    "dominance": 0.0,
                }
                ev = now_versions.get("pad", (None, 0))[1]
                if self.bb.try_write("pad", pad, ev, instance_id):
                    writes += 1
                else:
                    conflicts += 1
                ev2 = now_versions.get("dominant_emotion", (None, 0))[1]
                if self.bb.try_write("dominant_emotion", internal.get("dominant", "neutral"),
                                     ev2, instance_id):
                    writes += 1
                else:
                    conflicts += 1
                break

        # L1: PTSD
        for sr in l1:
            if sr.skill_name == "ptsd_trigger_check" and sr.success:
                ev = now_versions.get("ptsd_triggered", (None, 0))[1]
                if self.bb.try_write("ptsd_triggered", sr.output.get("triggered", False),
                                     ev, instance_id):
                    writes += 1
                else:
                    conflicts += 1
                break

        # L2: 防御
        for sr in l2:
            if sr.skill_name == "defense_mechanism_analysis" and sr.success:
                ev = now_versions.get("active_defense", (None, 0))[1]
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
                    ev = now_versions.get("pending_response", (None, 0))[1]
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
