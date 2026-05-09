"""Character Mind v2 — 现象学 Agent 运行时 (生产级 API)

架构反转: 连续意识流是主管道, CognitiveOrchestrator 是内部 Cognitive Frame。

使用:
    mind = CharacterMind(provider, character_profile)
    mind.perceive("陈风两小时没回消息")
    await mind.runtime.tick_once()
    response = mind.get_response()
    print(response.text)
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .registry import SkillRegistry, build_registry_from_profile
from .orchestrator import CognitiveOrchestrator
from .episodic_memory import EpisodicMemoryStore
from ..experimental.blackboard import Blackboard
from ..experimental.perception_stream import PerceptionStream
from ..experimental.behavior_stream import BehaviorStream
from ..experimental.phenomenological_runtime import PhenomenologicalRuntime
from ..experimental.love_state import LoveState
from ..experimental.memory_metabolism import MemoryMetabolism
from ..experimental.world_adapter import WorldAdapter


@dataclass
class CharacterResponse:
    """角色对当前 tick 的回应。"""
    text: str = ""
    action: str = "stay_silent"
    emotion: str = "neutral"
    subtext: str = ""
    internal_conflict: str = ""
    timestamp: float = 0.0


class CharacterMind:
    """生产级现象学 Agent 运行时。

    Attributes:
        runtime: 底层 PhenomenologicalRuntime
        blackboard: 共享状态黑板
        behavior: 行为流输出
        world: 世界适配器 (外部输入/输出)
    """

    def __init__(self, provider, character_profile: dict,
                 tick_interval: float = 0.5,
                 anti_alignment: bool = True,
                 biological_bridge=None):
        self.provider = provider
        self.character_profile = character_profile
        self.tick_interval = tick_interval

        # 核心基础设施
        self.blackboard = Blackboard()
        self.perception = PerceptionStream()
        self.behavior = BehaviorStream(character_profile.get("name", "角色"))
        self.world = WorldAdapter()

        # Skill 注册表 + Orchestrator (Cognitive Frame)
        registry = build_registry_from_profile(include_experimental=True)
        episodic = EpisodicMemoryStore()
        self.orchestrator = CognitiveOrchestrator(
            registry=registry,
            episodic_store=episodic,
            anti_alignment_enabled=anti_alignment,
            biological_bridge=biological_bridge,
        )

        # 初始化 Soul (核心身份)
        self.memory = MemoryMetabolism()
        self._init_soul(character_profile)

        # LoveState
        self.love = LoveState()

        # 运行时
        self.runtime = PhenomenologicalRuntime(
            blackboard=self.blackboard,
            perception_stream=self.perception,
            tick_s=tick_interval,
        )
        self.runtime.orchestrator = self.orchestrator
        self.runtime.provider = provider
        self.runtime.character_state = character_profile
        self.runtime.behavior_stream = self.behavior
        self.runtime.world_adapter = self.world
        self.runtime.love_state = self.love
        self.runtime.memory_metabolism = self.memory

        # 写入初始状态
        self.blackboard.write("dominant_emotion", "neutral")
        self.blackboard.write("pad", {"pleasure": 0.0, "arousal": 0.3, "dominance": 0.0})
        self.blackboard.write("conscious_workspace", [])
        self.blackboard.write("prediction_errors", {})
        self.blackboard.write("self_model", {
            "unresolved_conflict": "",
            "active_mask": "",
            "private_intention": "",
            "current_self_image": "我需要维持自己的体面。",
            "current_other_model": "对方的意图尚不明确。",
        })

        self._running = False
        self._task: asyncio.Task | None = None

    def _init_soul(self, profile: dict):
        """从角色配置初始化 soul.md 内容。"""
        p = profile.get("personality", {})
        t = profile.get("trauma", {})
        iw = profile.get("ideal_world", {})

        lines = [f"# {profile.get('name', '角色')} 的灵魂", ""]
        lines.append(f"OCEAN: O={p.get('openness',0.5):.1f} "
                     f"C={p.get('conscientiousness',0.5):.1f} "
                     f"E={p.get('extraversion',0.5):.1f} "
                     f"A={p.get('agreeableness',0.5):.1f} "
                     f"N={p.get('neuroticism',0.5):.1f}")
        lines.append(f"依恋风格: {p.get('attachment_style','secure')}")

        if p.get("defense_style"):
            lines.append(f"防御机制: {', '.join(p['defense_style'])}")

        schemas = t.get("active_schemas", [])
        for s in schemas:
            lines.append(f"- {s}")

        triggers = t.get("trauma_triggers", [])
        for tr in triggers:
            lines.append(f"- 触发: {tr}")

        if iw.get("ideal_self"):
            lines.append(f"理想自我: {iw['ideal_self']}")

        self.memory.set_soul("\n".join(lines))

    # ═══ 生命周期 ═══

    def start(self):
        """启动持续意识循环。"""
        if self._running:
            return
        self._running = True
        self.runtime.running = True
        self._task = asyncio.create_task(self.runtime._loop())

    def stop(self):
        """停止循环。"""
        self._running = False
        if self._task:
            self._task.cancel()

    # ═══ 输入 ═══

    def perceive(self, content: str, source: str = "external",
                 modality: str = "dialogue", intensity: float = 0.5):
        """角色感知到外部输入。"""
        if modality == "dialogue":
            self.perception.feed_dialogue(content, source, intensity)
        elif modality == "visual":
            self.perception.feed_visual(content, intensity, source)
        else:
            self.perception.feed_internal(content, intensity)
        self.runtime.last_external_input_t = time.time()

        # 外部输入是高显著性事件 → 提高预测误差
        self.blackboard.write("prediction_errors", {"L1_combined": 0.6})
        self.blackboard.write("conscious_workspace", [
            {"kind": "perception", "content": content[:160],
             "salience": 0.7, "source": "external"},
        ])

    def world_feedback(self, action: dict, result: str, valence: float):
        """世界反馈: 角色的行为产生了什么后果。"""
        self.world.feedback(action, result, valence)

    # ═══ 输出 ═══

    def get_response(self) -> CharacterResponse:
        """获取当前 tick 的角色回应。"""
        state = self.blackboard.read([
            "pending_response", "outer_behavior", "dominant_emotion",
            "self_model",
        ])
        outer = state.get("outer_behavior", {})
        return CharacterResponse(
            text=outer.get("content", ""),
            action=outer.get("type", "speech"),
            emotion=state.get("dominant_emotion", "neutral"),
            subtext=state.get("pending_response", {}).get("text", "")[:120],
            internal_conflict=state.get("self_model", {}).get("unresolved_conflict", ""),
            timestamp=time.time(),
        )

    def last_speech(self) -> str:
        """获取最近一次话语。"""
        speech = self.behavior.get_last_speech()
        return speech.get("content", "") if speech else ""

    # ═══ 状态查询 ═══

    def stats(self) -> dict:
        """运行时统计。"""
        return {
            **self.runtime.stats(),
            "behaviors": len(self.behavior),
            "world_events": len(self.world.events),
            "soul_defined": bool(self.memory.get_soul()),
        }

    def noise_report(self) -> str:
        """噪音报告 (Agent 可读)。"""
        return self.runtime.noise_manager.format_for_agent()

    def memory_index(self) -> str:
        """记忆指针索引。"""
        return self.memory.build_memory_index()

    # ═══ 持久化 ═══

    def save_state(self, directory: str):
        """保存完整状态到磁盘。"""
        self.memory.write_to_disk(directory)

    def to_dict(self) -> dict:
        return {
            "character_profile": self.character_profile,
            "tick_interval": self.tick_interval,
            "memory": self.memory.to_dict(),
            "love": self.love.to_dict(),
        }

    @classmethod
    def from_dict(cls, provider, data: dict) -> "CharacterMind":
        mind = cls(provider, data["character_profile"],
                   tick_interval=data.get("tick_interval", 0.5))
        if "memory" in data:
            mind.memory = MemoryMetabolism.from_dict(data["memory"])
            mind.runtime.memory_metabolism = mind.memory
        if "love" in data:
            mind.love = LoveState.from_dict(data["love"])
            mind.runtime.love_state = mind.love
        return mind
