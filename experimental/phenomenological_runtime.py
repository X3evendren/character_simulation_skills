"""Long-running phenomenological agent runtime.

每个 tick 的实际循环:
1. LoveState 演化 + 世界反馈消费
2. 空闲思维 (DMN)
3. Inner Stream 更新 (从 Blackboard 读取 self_model)
4. ExperientialField: Retention+Protention 更新 (纯数学, 零 token)
5. Cognitive Frame 触发 (L0-L3 频繁脉冲, ~1-3s 或预测误差时)
6. Memory Metabolism: 摄入→代谢
7. Expression Policy: 内部→外部 (masking/omission)
8. 行为发布 + 噪音管理 + 周期任务
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .inner_experience import InnerExperienceStream
from .expression_policy import ExpressionPolicy
from .experiential_field import ExperientialField
from .memory_metabolism import MemoryMetabolism
from .noise_manager import NoiseManager
from .skill_metabolism import SkillMetabolism
from .love_state import LoveState
from .feedback_loop import FeedbackLoop


@dataclass
class PhenomenologicalRuntime:
    blackboard: object
    perception_stream: object
    toca_runner: object | None
    tick_s: float = 1.0
    inner_stream: InnerExperienceStream = field(default_factory=InnerExperienceStream)
    expression_policy: ExpressionPolicy = field(default_factory=ExpressionPolicy)
    running: bool = False
    tick_count: int = 0
    _task: asyncio.Task | None = None
    world_adapter: object | None = None
    _last_feedback_count: int = 0
    behavior_stream: object | None = None
    _last_outer_behavior: dict | None = None
    idle_after_s: float = 5.0
    last_external_input_t: float = 0.0

    # 新模块
    experiential_field: ExperientialField = field(default_factory=ExperientialField)
    memory_metabolism: MemoryMetabolism = field(default_factory=MemoryMetabolism)
    skill_metabolism: SkillMetabolism = field(default_factory=SkillMetabolism)
    noise_manager: object | None = None
    love_state: LoveState = field(default_factory=LoveState)
    feedback_loop: FeedbackLoop = field(default_factory=FeedbackLoop)

    # orchestrator 引用 (用于 Cognitive Frame)
    orchestrator: object | None = None
    provider: object | None = None
    character_state: dict = field(default_factory=dict)

    # Cognitive Frame 触发
    cognitive_frame_cooldown: float = 1.0
    _last_cognitive_frame_t: float = 0.0
    _prediction_error_threshold: float = 0.3

    # 周期任务
    _metabolism_interval: int = 10          # 每N个tick运行一次记忆代谢
    _noise_check_interval: int = 20         # 每N个tick检查噪音

    def __post_init__(self):
        if self.noise_manager is None:
            self.noise_manager = NoiseManager(
                memory_metabolism=self.memory_metabolism,
                skill_metabolism=self.skill_metabolism,
            )

    # ═══ 生命周期 ═══

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        if self.toca_runner is not None:
            await self.toca_runner.start()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self.toca_runner is not None:
            await self.toca_runner.stop()

    async def _loop(self) -> None:
        while self.running:
            await self.tick_once()
            await asyncio.sleep(self.tick_s)

    # ═══ 主 Tick ═══

    async def tick_once(self) -> dict:
        self.tick_count += 1
        dt = self.tick_s

        # 1. 生物层: LoveState 演化
        self.love_state.tick(dt)

        # 2. 世界反馈消费
        self._consume_world_feedback()

        # 3. 空闲思维
        self._maybe_generate_idle_thought()

        # 4. 内部体验更新
        self._update_inner_stream()

        # 5. 体验场更新 (Retention+Protention)
        self._update_experiential_field()

        # 6. Cognitive Frame 触发 (L0-L3 情感脑+社会脑)
        if self._should_trigger_cognitive_frame():
            await self._trigger_cognitive_frame()

        # 7. 记忆摄入
        self._ingest_to_memory()

        # 8. 表达策略
        self._apply_expression_policy()

        # 9. 行为发布
        self._publish_outer_behavior()

        # 10. 周期任务
        if self.tick_count % self._metabolism_interval == 0:
            self.memory_metabolism.metabolize()
        if self.tick_count % self._noise_check_interval == 0:
            self._check_noise()

        # 11. 心跳
        heartbeat = {"t": time.time(), "tick": self.tick_count}
        self.blackboard.write("runtime_heartbeat", heartbeat)
        # 写入 LoveState 上下文
        self.blackboard.write("love_state", self.love_state.get_bio_context())
        return heartbeat

    # ═══ 体验场更新 ═══

    def _update_experiential_field(self) -> None:
        ws_state = self.blackboard.read(["conscious_workspace", "pad"])
        workspace = ws_state.get("conscious_workspace", [])
        if workspace:
            self.experiential_field.tick(workspace)
            retention_ctx = self.experiential_field.retention.format_for_context()
            if retention_ctx:
                self.blackboard.write("retention_context", retention_ctx)
            openness = self.experiential_field.protention.openness_score()
            self.blackboard.write("protention_openness", openness)
            # 注入前摄样本 (供 ThalamicGate 或 ConsciousnessLayer 使用)
            pad = ws_state.get("pad", {})
            samples = self.experiential_field.protention.sample_futures({
                "pleasure": pad.get("pleasure", 0.0),
                "arousal": pad.get("arousal", 0.5),
            })
            self.blackboard.write("protention_samples", samples)

    # ═══ Cognitive Frame 触发 ═══

    def _should_trigger_cognitive_frame(self) -> bool:
        """基于预测误差和显著性判断是否触发深度分析。"""
        now = time.time()
        if now - self._last_cognitive_frame_t < self.cognitive_frame_cooldown:
            return False

        # 读取预测误差
        errors = self.blackboard.read([
            "prediction_errors", "conscious_workspace",
        ])
        pred_errors = errors.get("prediction_errors", {})
        max_error = max(pred_errors.values()) if pred_errors else 0.0

        # 读取 workspace 显著性
        workspace = errors.get("conscious_workspace", [])
        max_salience = max(
            (item.get("salience", 0.0) for item in workspace),
            default=0.0,
        )

        return max_error > self._prediction_error_threshold or max_salience > 0.6

    async def _trigger_cognitive_frame(self) -> None:
        """运行 Cognitive Frame: orchestrator.process_event() (L0-L3 情感脑+社会脑)。

        从 Blackboard 和 PerceptionStream 构建事件, 调用 orchestrator,
        将结果写回 Blackboard。记录 Skills 代谢数据。
        """
        if self.orchestrator is None or self.provider is None:
            return

        self._last_cognitive_frame_t = time.time()

        # 构建事件: 感知窗口 + 当前心理状态 + 记忆上下文
        perception_window = self.perception_stream.get_window(10.0) if self.perception_stream else []
        snap = self.blackboard.read_with_versions()

        # 注入 LoveState 偏置到 character_state
        cs = dict(self.character_state) if self.character_state else {}
        if self.love_state.active:
            bio_ctx = self.love_state.get_bio_context()
            cs["_love_state"] = bio_ctx
            cs["_biological_drives"] = cs.get("_biological_drives", {})
            # PFC 抑制影响 personality 表现
            pfc = bio_ctx.get("pfc_inhibition", {})
            cs["_pfc_inhibition"] = pfc

        # 构建事件描述
        descriptions = []
        for p in perception_window[-5:]:
            src = f"[{p.get('source', '')}] " if p.get("source") else ""
            descriptions.append(f"{src}{p.get('content', '')}")
        event_desc = " ".join(descriptions) if descriptions else "内部思维"

        # 注入 Experiential Field 上下文
        retention_ctx = self.experiential_field.retention.format_for_context()
        protention_score = self.experiential_field.protention.openness_score()
        event_desc = (
            f"{retention_ctx}\n"
            f"[前摄敞开感: {protention_score:.2f}]\n"
            f"当前: {event_desc}"
        ).strip()

        # 从感知内容推断事件类型
        etype = self._infer_event_type(descriptions)
        # 从感知源提取 participants
        participants = []
        for p in perception_window[-3:]:
            src = p.get("source", "").strip()
            if src and src not in ("", "internal"):
                participants.append({"name": src, "relation": "acquaintance"})
        event = {
            "description": event_desc,
            "type": etype,
            "participants": participants,
            "significance": 0.4,
            "tags": ["cognitive_frame"],
            "_phenomenological_tick": self.tick_count,
        }

        try:
            result = await self.orchestrator.process_event(self.provider, cs, event)

            # 写回 Blackboard
            for layer, skill_results in result.layer_results.items():
                for sr in skill_results:
                    if not sr.success:
                        continue
                    # 记录 Skills 代谢
                    self.skill_metabolism.record(
                        sr.skill_name, sr.tokens_used,
                        sr.parse_success, 0.5,
                    )
                    # 写回关键输出
                    if sr.skill_name == "plutchik_emotion":
                        internal = sr.output.get("internal", {})
                        self.blackboard.write("dominant_emotion", internal.get("dominant", "neutral"))
                        self.blackboard.write("pad", {
                            "pleasure": internal.get("pleasantness", 0.0),
                            "arousal": internal.get("intensity", 0.5),
                        })
                    elif sr.skill_name == "response_generator":
                        self.blackboard.write("pending_response", {
                            "text": sr.output.get("response_text", ""),
                            "confidence": 0.8,
                        })

            self.blackboard.write("last_cognitive_result", {
                "t": time.time(), "tokens": result.total_tokens,
                "tick": self.tick_count,
            })

        except Exception as e:
            self.blackboard.write("cognitive_frame_error", str(e))

    # ═══ 记忆摄入 ═══

    def _ingest_to_memory(self) -> None:
        """将 InnerExperienceStream 中的新内容摄入记忆代谢系统。"""
        recent = self.inner_stream.recent(3)
        for item in recent:
            content = item.get("content", "")
            if not content:
                continue
            intensity = item.get("intensity", 0.5)
            emotion = {item.get("kind", "unknown"): intensity}
            significance = max(0.0, min(1.0, intensity))
            tags = [item.get("kind", ""), item.get("source", "")]
            # 避免重复摄入: 检查所有层级
            all_memories = (
                self.memory_metabolism.working +
                self.memory_metabolism.short_term +
                self.memory_metabolism.long_term
            )
            already_ingested = any(m.content == content for m in all_memories[-20:])
            if not already_ingested:
                self.memory_metabolism.ingest(content, emotion, significance, tags)

    # ═══ 噪音管理 ═══

    def _check_noise(self) -> None:
        report = self.noise_manager.report()
        self.blackboard.write("noise_report", report)
        if report["auto_clean_triggered"]:
            self._auto_clean_noise()

    def _auto_clean_noise(self) -> None:
        """自动清理: 触发记忆代谢淘汰。"""
        self.memory_metabolism.metabolize()

    # ═══ 内部体验更新 ═══

    def _update_inner_stream(self) -> None:
        state = self.blackboard.read([
            "dominant_emotion", "self_model", "conscious_workspace", "pad",
        ])
        emotion = state.get("dominant_emotion")
        if emotion:
            self.inner_stream.append("felt_emotion", emotion, 0.6, "blackboard", True)

        self_model = state.get("self_model", {})
        conflict = self_model.get("unresolved_conflict", "")
        if conflict:
            self.inner_stream.append("private_conflict", conflict, 0.75, "self_model", False)

        intention = self_model.get("private_intention", "")
        if intention:
            self.inner_stream.append("private_intention", intention, 0.7, "self_model", False)

        self.blackboard.write("inner_experience", self.inner_stream.to_dict())

    # ═══ 世界反馈消费 ═══

    def _consume_world_feedback(self) -> None:
        if self.world_adapter is None:
            return
        feedback = getattr(self.world_adapter, "feedback_events", [])
        new_items = feedback[self._last_feedback_count:]
        self._last_feedback_count = len(feedback)
        for item in new_items:
            intensity = abs(item.get("valence", 0.0))
            expressible = item.get("valence", 0.0) >= 0
            self.inner_stream.append(
                "action_consequence",
                item.get("result", ""),
                intensity,
                "world_feedback",
                expressible,
            )
        if new_items:
            self.blackboard.write("last_world_feedback", new_items[-1])
            # FeedbackLoop: 模式提取 + 知识固化 + 成长日记
            for item in new_items:
                self.feedback_loop.record_feedback(
                    item.get("action", {}),
                    item.get("result", ""),
                    item.get("valence", 0.0),
                )
            diary = self.feedback_loop.generate_growth_diary(self.memory_metabolism)
            if diary:
                self.blackboard.write("growth_diary_entry", diary)

    # ═══ 表达策略 ═══

    def _apply_expression_policy(self) -> None:
        state = self.blackboard.read(["pending_response", "self_model"])
        response = state.get("pending_response")
        if not isinstance(response, dict) or not response.get("text"):
            return
        self_model = state.get("self_model", {})
        inner_items = self.inner_stream.recent(8, include_private=True)
        composed = self.expression_policy.compose(
            inner_items,
            self_model,
            proposed_text=response.get("text", ""),
        )
        outer = composed["outer"]
        self.blackboard.write("outer_behavior", outer)
        if composed["mechanism"] != "direct_expression" and composed.get("inner_used"):
            self.inner_stream.record_divergence(
                inner=composed["inner_used"][0],
                outer=outer,
                mechanism=composed["mechanism"],
            )

    # ═══ 行为流发布 ═══

    def _publish_outer_behavior(self) -> None:
        if self.behavior_stream is None:
            return
        outer = self.blackboard.read(["outer_behavior"]).get("outer_behavior")
        if not isinstance(outer, dict) or not outer.get("content"):
            return
        if self._last_outer_behavior == outer:
            return
        self._last_outer_behavior = dict(outer)
        btype = outer.get("type", "speech")
        self.behavior_stream.emit(btype, outer["content"], outer.get("confidence", 0.8))

    # ═══ 空闲思维 ═══

    def _maybe_generate_idle_thought(self) -> None:
        now = time.time()
        if self.last_external_input_t and now - self.last_external_input_t < self.idle_after_s:
            return
        state = self.blackboard.read(["self_model", "dominant_emotion"])
        conflict = state.get("self_model", {}).get("unresolved_conflict", "")
        if conflict:
            self.inner_stream.append(
                "spontaneous_thought",
                f"空闲时反复回到这个冲突: {conflict}",
                0.55,
                "idle_mentation",
                False,
            )

    @staticmethod
    def _infer_event_type(descriptions: list[str]) -> str:
        """从感知内容关键词推断事件类型。"""
        text = " ".join(descriptions).lower()
        if any(w in text for w in ("冲突", "争吵", "骂", "conflict", "argument")):
            return "conflict"
        if any(w in text for w in ("爱", "喜欢", "想你", "love", "miss you", "romantic")):
            return "romantic"
        if any(w in text for w in ("背叛", "骗", "betrayal", "secret")):
            return "betrayal"
        if any(w in text for w in ("死", "威胁", "危险", "death", "threat", "danger")):
            return "threat"
        if any(w in text for w in ("道德", "应该", "不该", "moral", "choice")):
            return "moral_choice"
        if any(w in text for w in ("权威", "师父", "老板", "master", "superior", "authority")):
            return "social"
        if any(w in text for w in ("你", "他", "她", "你们", "回", "说")):
            return "social"
        return "routine"

    # ═══ 状态查询 ═══

    def stats(self) -> dict:
        return {
            "tick_count": self.tick_count,
            "memory": self.memory_metabolism.noise_report(),
            "noise": self.noise_manager.report(),
            "experiential_field_items": len(self.experiential_field.retention.items),
            "protention_openness": self.experiential_field.protention.openness_score(),
        }
