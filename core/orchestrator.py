"""五层时序编排器 — 基于 CLARION 认知架构 + Scherer 评估理论

- 情感半衰期衰减 (Sentipolis, 2026): PAD连续情感 + 双速动力学
- 事件记忆 (AdaMem + MENTOR, 2026): Episodic Memory with emotional tagging
- 人格状态机 (Dynamic State Machines, 2026): 情境化OCEAN
- 理想世界张力 (DiriGent, 2025): Ideal World vs Reality gap
- 自我中心上下文投射 (SPASM, 2026): Egocentric Context Projection
- 反RLHF模板偏差 (Nature MI, 2025): Anti-alignment bias injection

同层并行，跨层串行。
Layer 0 始终在线。Layer 3 按触发条件选择。Layer 4-5 仅在关键场景激活。

事件 → [情感衰减/记忆检索/状态更新] → L0人格滤镜 → L1快速前意识
     → L2意识层 → L3关系/社会 → L4反思 → L5状态更新
     → [情感残留存储/记忆存储/状态持久化]
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import SkillResult
from .registry import get_registry
from .emotion_decay import (
    EmotionDecayModel, PADState, plutchik_to_pad, pad_to_plutchik,
)
from .episodic_memory import EpisodicMemory, EpisodicMemoryStore
from .personality_state_machine import PersonalityStateMachine
from .conversation_history import ConversationHistoryStore, ConversationTurn


@dataclass
class CognitiveResult:
    """一次完整认知处理的结果"""
    layer_results: dict[int, list[SkillResult]] = field(default_factory=dict)
    combined_analysis: str = ""
    state_changes: list[dict] = field(default_factory=list)
    total_tokens: int = 0
    errors: list[str] = field(default_factory=list)
    # 新增持久化状态字段
    updated_emotion_decay: dict = field(default_factory=dict)
    updated_personality_state: dict = field(default_factory=dict)
    episodic_memory_stored: bool = False
    mood_bias: dict = field(default_factory=dict)
    # 自适应管道记录
    adaptive_info: dict = field(default_factory=dict)  # skipped_layers, reason, prediction_error, salience


class CognitiveOrchestrator:
    """五层认知编排器

    Attributes:
        registry: Skill注册表
        episodic_store: 事件记忆存储
        conversation_store: 外置对话历史
        anti_alignment_enabled: 是否启用反RLHF模板偏差
    """

    def __init__(self, episodic_store: EpisodicMemoryStore | None = None,
                 conversation_store: ConversationHistoryStore | None = None,
                 anti_alignment_enabled: bool = True,
                 biological_bridge=None,
                 registry=None,
                 adaptive_skip: bool = True):
        self.registry = registry or get_registry()
        self.episodic_store = episodic_store or EpisodicMemoryStore()
        self.conversation_store = conversation_store
        self.anti_alignment_enabled = anti_alignment_enabled
        self.bio_bridge = biological_bridge
        self.adaptive_skip = adaptive_skip
        self._last_event_time: float = 0.0
        # 自适应阈值
        self._skip_prediction_error_max: float = 0.3
        self._skip_salience_max: float = 0.6

    # ═══════════════════════════════════════════════════════════
    # 主处理流程
    # ═══════════════════════════════════════════════════════════

    async def process_event(
        self,
        provider,
        character_state: dict,
        event: dict,
        context: dict | None = None,
    ) -> CognitiveResult:
        """处理一个事件 — 运行完整的五层认知流程"""
        result = CognitiveResult()
        ctx = context or {}

        # ── 生物基础层更新 (L-3 → L-1) ──
        now = time.time()
        dt = now - self._last_event_time if self._last_event_time > 0 else 60.0
        self._last_event_time = now
        if self.bio_bridge is not None:
            bio_ctx = self.bio_bridge.before_event(event, dt_seconds=dt)
            ctx["biological_context"] = bio_ctx

        # ── 情感衰减 + 记忆检索 + 状态更新 ──
        ctx = self._prepare_context(character_state, event, ctx)

        # 事件触发条件 (统一计算，供各层 Skill 选择使用)
        event_triggers = self._compute_event_triggers(event)

        # SPASM 自我中心上下文投射 — 每事件计算一次
        projected_ctx = self._project_egocentric_context(ctx, character_state)

        # ── Layer 0: 人格滤镜 — 使用情境化OCEAN ──
        l0_skills = self._get_layer_skills(0, event_triggers)
        l0_prompt_override = self._get_layer0_bias(ctx)
        l0 = await self._run_layer(0, l0_skills, provider, character_state, event, ctx,
                                   projected_ctx, system_hint=l0_prompt_override)
        result.layer_results[0] = l0
        ctx["l0"] = [s.output for s in l0 if s.success]

        # ── Layer 1: 快速前意识 — 并行 ──
        l1_skills = self._get_layer_skills(1, event_triggers)
        l1 = await self._run_layer(1, l1_skills, provider, character_state, event, ctx, projected_ctx)
        result.layer_results[1] = l1
        ctx["l1"] = [s.output for s in l1 if s.success]

        # ── 自适应跳过判断 ──
        # 从上下文读取预测数据，决定是否跳过 L2-L4 深度评估
        pred_ctx = ctx.get("_prediction_context") or {}
        should_skip_deep = self._should_skip_deep_layers(event, event_triggers, pred_ctx)
        if should_skip_deep:
            result.adaptive_info = {
                "skipped_layers": [2, 3, 4],
                "reason": pred_ctx.get("reason", "low_prediction_error"),
                "prediction_error": pred_ctx.get("max_error", 0.0),
                "salience": pred_ctx.get("max_salience", 0.0),
            }
            # 跳过 L2-L4，直接进入 L5 回应生成
            # L2-L3-L4 的结果设为空列表，保持 ctx 结构完整
            for layer in (2, 3, 4):
                result.layer_results[layer] = []
                ctx[f"l{layer}"] = []
        else:
            # ── Layer 2: 意识层情绪评估 — 并行 ──
            l2_skills = self._get_layer_skills(2, event_triggers)
            l2 = await self._run_layer(2, l2_skills, provider, character_state, event, ctx, projected_ctx)
            result.layer_results[2] = l2
            ctx["l2"] = [s.output for s in l2 if s.success]

            # ── Layer 3: 关系/社会处理 — 按触发条件选择性激活 ──
            l3_skills = self._get_layer_skills(3, event_triggers)
            if l3_skills:
                l3 = await self._run_layer(3, l3_skills, provider, character_state, event, ctx, projected_ctx)
                result.layer_results[3] = l3
                ctx["l3"] = [s.output for s in l3 if s.success]

            # ── Layer 4: 反思处理 — 仅在关键场景激活 ──
            if self._is_significant(event, result):
                l4_skills = self._get_layer_skills(4, event_triggers)
                if l4_skills:
                    l4 = await self._run_layer(4, l4_skills, provider, character_state, event, ctx, projected_ctx)
                    result.layer_results[4] = l4
                    ctx["l4"] = [s.output for s in l4 if s.success]

        # ── Layer 5: 状态更新 + 回应生成 — 串行（始终运行，不受自适应跳过影响） ──
        has_trauma = "trauma" in event_triggers
        has_reflective = "reflective" in event_triggers
        l5_skill_names = ["response_generator"]
        if has_trauma or has_reflective:
            l5_skill_names.insert(0, "young_schema_update")
        if has_trauma:
            l5_skill_names.insert(0, "ace_trauma_processing")
        l5_skills = [s for s in l5_skill_names if s in self.registry]
        if l5_skills:
            # 回应生成器需要反RLHF提示词；分析层不需要
            l5 = await self._run_layer(5, l5_skills, provider, character_state, event, ctx, projected_ctx)
            result.layer_results[5] = l5
            ctx["l5"] = [s.output for s in l5 if s.success]

        # ── 提取回应文本 ──
        l5_outputs = ctx.get("l5", [])
        for out in l5_outputs:
            if out.get("response_text"):
                result.state_changes = [{"response_text": out.get("response_text")}]
                result.combined_analysis = out.get("response_text", "")
                break

        # ── 持久化状态 ──
        self._persist_state(character_state, event, result, ctx)

        # ── 汇总 ──
        result.total_tokens = sum(
            s.tokens_used
            for layer_results in result.layer_results.values()
            for s in layer_results
        )
        result.errors = [
            s.error
            for layer_results in result.layer_results.values()
            for s in layer_results
            if not s.success and s.error
        ]

        # ── 生物基础层反馈 ──
        if self.bio_bridge is not None:
            self.bio_bridge.after_event(event, result)

        return result

    # ═══════════════════════════════════════════════════════════
    # 上下文准备 (情感衰减 + 记忆 + 状态机)
    # ═══════════════════════════════════════════════════════════

    def _prepare_context(self, character_state: dict, event: dict, ctx: dict) -> dict:
        """准备增强上下文: 应用情感衰减、检索记忆、更新人格状态、注入偏差"""

        # 1. 情感衰减: 读取上次残留 → 衰减 → 注入为 mood_bias
        decay_data = character_state.get("emotion_decay")
        if decay_data:
            decay_model = EmotionDecayModel.from_dict(decay_data)
            decay_model.decay(dt_events=1.0)
        else:
            decay_model = EmotionDecayModel()
        ctx["mood_bias"] = decay_model.get_mood_bias()
        ctx["emotion_decay_model"] = decay_model  # 传递对象引用，process_event结尾持久化

        # 生物层调制: CORT调节情绪衰减半衰期, 驱力注入角色状态
        bio = ctx.get("biological_context", {})
        if bio:
            cort = bio.get("hpa", {}).get("cortisol", bio.get("neurotransmitters", {}).get("CORT", 0.3))
            decay_model.set_cortisol_modulation(cort)
            # 将驱力状态注入character_state供后续使用
            character_state["_biological_drives"] = bio.get("drives", {})
            character_state["_biological_nt"] = bio.get("neurotransmitters", {})

        # 2. 事件记忆检索 + 冻结快照 — 使用混合检索
        event_type = event.get("type", "unknown")
        event_tags = event.get("tags", [])
        relevant_memories = self.episodic_store.search_hybrid(
            event_type=event_type, n=5, tags=event_tags,
        )
        if relevant_memories:
            ctx["episodic_memories"] = [m.to_dict() for m in relevant_memories]
        ctx["recent_events"] = self.episodic_store.get_recent_descriptions(5)
        ctx["memory_snapshot"] = self.episodic_store.format_snapshot_for_prompt()

        # 3. 人格状态机: 根据事件类型更新状态
        psm_data = character_state.get("personality_state_machine")
        if psm_data:
            psm = PersonalityStateMachine.from_dict(psm_data)
        else:
            # 从 character_state 的 personality 字段初始化基线
            pers = character_state.get("personality", {})
            from .personality_state_machine import OCEANProfile
            baseline = OCEANProfile.from_dict(pers)
            psm = PersonalityStateMachine(baseline=baseline)

        # 判定权威关系
        participants = event.get("participants", [])
        has_authority = any(
            p.get("role") in ("master", "elder", "official", "superior")
            for p in participants
        )
        emotion_hint = {
            "dominant": "",
            "pleasantness": 0.0,
            "intensity": 0.5,
        }
        state_transition = psm.update_state(event_type, emotion_hint, has_authority)
        ctx["personality_state_machine"] = psm
        ctx["personality_state"] = {
            "current_state": psm.current_state,
            "state_description": psm.get_state_description(),
            "transition": state_transition,
        }
        # 情境化OCEAN存入ctx供Layer 0使用
        active_ocean = psm.get_active_profile()
        ctx["_active_ocean"] = active_ocean.to_dict()

        # 4. 反RLHF模板偏差: 注入系统级指令片段（角色特异性）
        # 低显著性事件使用精简版提示以节省token
        if self.anti_alignment_enabled:
            sig = event.get("significance", 0.5)
            if sig >= 0.5:
                ctx["_anti_alignment_hint"] = self._build_anti_alignment_hint(character_state)
            else:
                ctx["_anti_alignment_hint"] = "【角色锚定】行为由此心理画像驱动，不施加外部规范。回应简短(2-3句)，不解释动机。"

        # 5. 外置对话历史
        if self.conversation_store:
            ctx["external_history"] = self.conversation_store.format_history_string()
            ctx["external_history_compact"] = self.conversation_store.format_compact_context()
            ctx["time_since_last_turn"] = self.conversation_store.time_since_last_turn()
        else:
            ctx["external_history"] = "没有对话记录"
            ctx["external_history_compact"] = "之前没有对话"

        return ctx

    def _build_anti_alignment_hint(self, cs: dict) -> str:
        """构建角色特异性的行为约束提示。

        沉默法则 (Silence Rule): 永远不说"不要X"——
        这会激活X的token权重。只正面描述角色是什么、做什么。
        """
        p = cs.get("personality", {})
        a = p.get("agreeableness", 0.5)
        n = p.get("neuroticism", 0.5)
        c = p.get("conscientiousness", 0.5)
        e = p.get("extraversion", 0.5)
        o = p.get("openness", 0.5)
        defense = p.get("defense_style", [])
        attachment = p.get("attachment_style", "secure")
        schemas = cs.get("trauma", {}).get("active_schemas", [])
        ideal = cs.get("ideal_world", {})

        parts = []

        # 锚定声明
        parts.append("【角色锚定】行为由此心理画像驱动，不施加外部规范:")

        # 核心人格 — 压缩为关键特征
        trait_descriptions = []
        if n >= 0.75:
            trait_descriptions.append(f"神经质极高({n:.1f})——高度焦虑、灾难化、易崩溃")
        elif n >= 0.55:
            trait_descriptions.append(f"神经质偏高({n:.1f})——易焦虑、威胁敏感")
        if a <= 0.25:
            trait_descriptions.append(f"宜人性极低({a:.1f})——自我中心、冷漠、可操控他人")
        elif a <= 0.45:
            trait_descriptions.append(f"宜人性偏低({a:.1f})——警惕怀疑、优先自身利益")
        elif a >= 0.7:
            trait_descriptions.append(f"宜人性高({a:.1f})——迎合顺从、难以拒绝")
        if c <= 0.3:
            trait_descriptions.append(f"尽责性低({c:.1f})——冲动随性、不顾后果")
        if e <= 0.35:
            trait_descriptions.append(f"外向性低({e:.1f})——内敛私密、公共场合克制")
        if trait_descriptions:
            parts.append("核心人格: " + " ".join(trait_descriptions))

        # 依恋风格
        attachment_behaviors = {
            "anxious": "依恋:焦虑型——需要不断确认，对被抛弃极度敏感，会黏附追问试探",
            "avoidant": "依恋:回避型——用距离保护自己，靠近时撤退，撤退时感到安全",
            "fearful_avoidant": "依恋:恐惧-回避型——渴望又恐惧亲密，反复推拉，无法信任",
            "secure": "依恋:安全型——坦然给予和接受爱",
        }
        if attachment in attachment_behaviors:
            parts.append(attachment_behaviors[attachment])

        # 防御机制
        if defense:
            defense_cn = "、".join(defense)
            parts.append(f"防御机制: {defense_cn}——扭曲现实、投射、反向形成、合理化")

        # 图式 — 深层行为驱动
        schema_behaviors = {
            "屈从": "屈从图式:无法坚持边界，默认屈服妥协，'不行'=害羞而非拒绝",
            "情感剥夺": "情感剥夺图式:深信无人能满足自己，被需要=氧气，会不顾一切抓住",
            "缺陷/羞耻": "缺陷/羞耻图式:深信真面目会被厌恶，被接纳时产生压倒性的依恋感激",
            "不信任/虐待": "不信任图式:默认预期被伤害，被善待时困惑感动→超常回报",
            "遗弃/不稳定": "遗弃图式:深信重要之人终将离开，会牺牲一切维系关系",
        }
        for schema_name in schemas:
            if schema_name in schema_behaviors:
                parts.append(schema_behaviors[schema_name])

        # 理想世界
        if ideal:
            ideal_self = ideal.get("ideal_self", "")
            if ideal_self:
                parts.append(f"理想自我:'{ideal_self}'。与现实的差距是驱动行为的核心矛盾")

        # 收束 — 高开放性角色允许自我反思，其他角色保持约束
        if o >= 0.7:
            parts.append(
                "【行为约束】回应简短(2-3句)。可以自我反思和质疑——这是你人格的一部分。"
                "但仍用情境传达潜台词，不要把弦外之音翻译成明台词。"
            )
        else:
            parts.append(
                "【行为约束】回应简短(2-3句)，不解释动机，不分析自己。"
                "潜台词留给情境传达——不把弦外之音翻译成明台词。"
                "呈现角色的本来面目，情绪失控、自欺欺人、边界模糊等都在行为范围内。"
            )

        # 生物层驱力调制
        drives = cs.get("_biological_drives", {})
        if drives:
            urgent = [k for k, v in drives.items() if v > 0.7]
            if urgent:
                parts.append(f"【驱力状态】当前最紧迫的内在需求: {', '.join(urgent)}。这会影响行为优先级。")
            dominant = max(drives, key=drives.get) if drives else None
            if dominant and drives.get(dominant, 0) > 0.5:
                parts.append(f"主导驱力: {dominant}({drives[dominant]:.0%})——影响回应的动机倾向。")

        return "\n".join(parts)

    def _get_layer0_bias(self, ctx: dict) -> str | None:
        """获取Layer 0 (BigFive) 的情境化偏置提示"""
        active = ctx.get("_active_ocean")
        if not active:
            return None
        return (
            f"当前情境人格状态已从基线偏移: "
            f"O={active['openness']:.2f} C={active['conscientiousness']:.2f} "
            f"E={active['extraversion']:.2f} A={active['agreeableness']:.2f} "
            f"N={active['neuroticism']:.2f}"
        )

    # ═══════════════════════════════════════════════════════════
    # 状态持久化
    # ═══════════════════════════════════════════════════════════

    def _persist_state(self, character_state: dict, event: dict,
                       result: CognitiveResult, ctx: dict) -> None:
        """将处理后的状态写回 character_state"""

        # 1. 情感衰减持久化
        decay_model: EmotionDecayModel = ctx.get("emotion_decay_model")
        if decay_model:
            # 从 Layer 1 提取情感数据更新衰减模型
            self._update_decay_from_l1(decay_model, ctx, event)
            character_state["emotion_decay"] = decay_model.to_dict()
            result.updated_emotion_decay = decay_model.to_dict()
            result.mood_bias = decay_model.get_mood_bias()

        # 2. 事件记忆存储
        significance = event.get("significance", 0.5)
        # 只有中等以上显著性的事件才存入记忆
        if significance >= 0.3:
            l1_data = ctx.get("l1", [{}])[0] if ctx.get("l1") else {}
            internal = l1_data.get("internal", {})
            emotions = internal.get("emotions", l1_data.get("emotions", {}))
            memory = EpisodicMemory(
                timestamp=time.time(),
                description=event.get("description", ""),
                emotional_signature=emotions,
                significance=significance,
                event_type=event.get("type", "unknown"),
                tags=event.get("tags", []),
            )
            self.episodic_store.store(memory)
            result.episodic_memory_stored = True

        # 3. 人格状态持久化
        psm: PersonalityStateMachine = ctx.get("personality_state_machine")
        if psm:
            character_state["personality_state_machine"] = psm.to_dict()
            result.updated_personality_state = psm.to_dict()

        # 4. Clean up temp fields
        ctx.pop("_active_ocean", None)

    def _update_decay_from_l1(self, decay_model: EmotionDecayModel,
                              ctx: dict, event: dict) -> None:
        """从 Layer 1 的结果更新情感衰减模型"""
        l1_outputs = ctx.get("l1", [])
        if not l1_outputs:
            return

        l1 = l1_outputs[0]
        internal = l1.get("internal", {})
        emotions = internal.get("emotions", l1.get("emotions", {}))

        if emotions:
            event_pad = plutchik_to_pad(emotions)
            significance = event.get("significance", 0.5)
            decay_model.apply_event(event_pad, significance)

    # ═══════════════════════════════════════════════════════════
    # 核心执行引擎
    # ═══════════════════════════════════════════════════════════

    async def _run_layer(
        self, layer: int, skill_names: list[str],
        provider, character_state: dict, event: dict, context: dict,
        projected_context: dict,
        system_hint: str | None = None,
    ) -> list[SkillResult]:
        """并行执行同一层的所有 Skill。

        反RLHF提示词仅在 Layer 5 注入。
        system_hint 仅在 Layer 0 注入（情境化 OCEAN 偏置）。
        """
        if not skill_names:
            return []

        async def run_one(name: str) -> SkillResult:
            skill = self.registry.get(name)
            if skill is None:
                return SkillResult(
                    skill_name=name, layer=layer, output={},
                    success=False, error=f"Skill not found: {name}"
                )

            # 每层只接收前几层的输出 (避免跨层未来数据泄漏)
            enhanced_context = {
                **projected_context,
                "mood_bias": context.get("mood_bias", {}),
                "episodic_memories": context.get("episodic_memories", []),
                "recent_events": context.get("recent_events", []),
                "personality_state": context.get("personality_state", {}),
            }
            # 注入已完成层的输出 (L0 → L1, L1 → L2, etc.)
            for prev_layer in range(layer):
                key = f"l{prev_layer}"
                enhanced_context[key] = context.get(key, [])

            # 情境化 OCEAN 偏置仅在 Layer 0 注入
            if layer == 0 and system_hint:
                enhanced_context["_situational_ocean_hint"] = system_hint
            # 反RLHF提示词仅在回应生成层注入
            if layer == 5:
                enhanced_context["_anti_alignment_hint"] = context.get("_anti_alignment_hint", "")

            return await skill.run(provider, character_state, event, enhanced_context)

        return await asyncio.gather(*[run_one(name) for name in skill_names])

    def _project_egocentric_context(self, context: dict,
                                     character_state: dict) -> dict:
        """SPASM Egocentric Context Projection.

        将共享事件历史投射为角色的"第一人称"视角。
        当前为单角色版本——将来多角色时每个角色获得独立投射。

        核心原则: 事件描述不标注"SELF/PARTNER"角色标签，
        而是从当前角色的视角重新解释事件。
        """
        projected = {}

        # 投射最近事件为自我中心视角
        recent = context.get("recent_events", [])
        if recent:
            projected["egocentric_recent"] = [
                f"[你的记忆] {desc}" for desc in recent
            ]

        # 情绪偏置投射
        mood = context.get("mood_bias", {})
        if mood:
            mood_congruence = mood.get("mood_congruence_bias", "neutral")
            if mood_congruence == "negative":
                projected["mood_lens"] = "当前情绪残留偏负面——角色可能对事件做出更悲观的解读"
            elif mood_congruence == "positive":
                projected["mood_lens"] = "当前情绪残留偏正面——角色可能对事件做出更乐观的解读"

        # 人格状态投射
        pstate = context.get("personality_state", {})
        if pstate:
            projected["state_lens"] = (
                f"当前人格状态: {pstate.get('current_state', 'baseline')} "
                f"({pstate.get('state_description', '')})"
            )

        # 外置对话历史投射 — 从角色第一人称视角
        external_history = context.get("external_history", "")
        if external_history and external_history != "没有对话记录":
            projected["conversation_context"] = (
                f"之前的对话记录（从你的视角）: {external_history}"
            )

        return projected

    # ═══════════════════════════════════════════════════════════
    # Skill 选择 (统一入口, profile 为单一真理源)
    # ═══════════════════════════════════════════════════════════

    def _compute_event_triggers(self, event: dict) -> list[str]:
        """从事件中提取触发条件标签，供各层 Skill 匹配。"""
        event_type = event.get("type", "")
        participants = event.get("participants", [])

        has_partner = any(p.get("relation") in ("partner", "lover", "crush") for p in participants)
        has_authority = any(p.get("role") in ("master", "elder", "official", "superior") for p in participants)
        has_conflict = event_type in ("conflict", "battle", "confrontation", "argument")
        has_resources = event_type in ("trade", "auction", "resource_allocation")
        has_group = len(participants) > 2
        has_social = event_type in ("social", "romantic") or len(participants) > 0

        triggers = []
        if has_partner: triggers.append("romantic")
        if has_authority: triggers.append("authority")
        if has_conflict: triggers.append("conflict")
        if has_resources: triggers.append("economic")
        if has_group: triggers.append("group")
        if has_social: triggers.append("social")
        if event_type in ("trauma", "betrayal", "death") or "trauma" in event.get("tags", []):
            triggers.append("trauma")
        if event.get("significance", 0) >= 0.5:
            triggers.append("reflective")

        # moral 触发: 事件类型或标签
        if event_type in ("moral_choice", "confession") or "moral" in event.get("tags", []):
            triggers.append("moral")

        return triggers

    def _get_layer_skills(self, layer: int, event_triggers: list[str]) -> list[str]:
        """从 registry 获取某层的 Skill，按触发条件匹配。

        "always" 触发条件的 Skill 始终选中。
        其余 Skill 仅当 event_triggers 与其触发条件有交集时选中。
        """
        all_layer = self.registry.list_by_layer(layer)
        if not all_layer:
            return []

        event_set = set(event_triggers)
        selected = []
        for name in all_layer:
            skill = self.registry.get(name)
            if skill is None:
                continue
            skill_triggers = set(skill.meta.trigger_conditions)
            if "always" in skill_triggers or (event_set & skill_triggers):
                selected.append(name)

        return selected

    def _select_l3(self, character_state: dict, event: dict) -> list[str]:
        """按触发条件选择性激活 Layer 3 Skill (向后兼容)。"""
        return self._get_layer_skills(3, self._compute_event_triggers(event))

    # ═══════════════════════════════════════════════════════════
    # Layer 4 激活判断
    # ═══════════════════════════════════════════════════════════

    def _is_significant(self, event: dict, result: CognitiveResult) -> bool:
        """判断是否需要激活 Layer 4 反思处理"""
        event_type = event.get("type", "")
        significance = event.get("significance", 0)

        if significance >= 0.70:
            return True
        if event_type in ("moral_choice", "betrayal", "death", "breakthrough", "confession"):
            return True

        # Layer 2 高情绪强度
        l2 = result.layer_results.get(2, [])
        for s in l2:
            if s.success and s.output.get("emotional_intensity", 0) >= 0.8:
                return True

        # 同类型历史事件 >= 3 → 可能需要反思
        same_type_count = len(self.episodic_store.get_by_type(event_type, 10))
        if same_type_count >= 3:
            return True

        return False

    # ═══════════════════════════════════════════════════════════
    # 自适应管道控制
    # ═══════════════════════════════════════════════════════════

    def _should_skip_deep_layers(
        self, event: dict, event_triggers: list[str], pred_ctx: dict,
    ) -> bool:
        """判断是否应跳过 L2-L4 深度评估。

        条件：
        - adaptive_skip 已启用
        - 非 trauma 事件（trauma 始终走完整管道）
        - 预测误差低于阈值 且 显著性低于阈值
        - 非 moral_choice/betrayal/death/confession 类型
        """
        if not self.adaptive_skip:
            return False

        # trauma 事件始终完整处理
        if "trauma" in event_triggers:
            return False

        # 关键事件类型不跳过
        event_type = event.get("type", "")
        if event_type in ("moral_choice", "betrayal", "death", "breakthrough", "confession"):
            return False

        # 高显著性事件不跳过
        if event.get("significance", 0) >= 0.7:
            return False

        max_error = pred_ctx.get("max_error", 1.0)
        max_salience = pred_ctx.get("max_salience", 1.0)

        return max_error < self._skip_prediction_error_max and max_salience < self._skip_salience_max

    # ═══════════════════════════════════════════════════════════
    # 多Agent交互处理
    # ═══════════════════════════════════════════════════════════

    async def process_multi_agent_turn(
        self,
        provider,
        characters: dict[str, dict],
        shared_event: dict,
        speaker_id: str,
        listener_ids: list[str],
        conversation_history: list[dict] | None = None,
    ) -> dict:
        """处理一轮多agent对话.

        当前发言者运行完整认知管道。
        其他角色的状态机在发言后接收micro_update。
        所有角色共享事件记忆。

        Args:
            provider: LLM provider
            characters: {角色名: character_state}
            shared_event: 共享事件描述
            speaker_id: 当前说话的角色ID
            listener_ids: 倾听者角色ID列表
            conversation_history: 之前的对话历史 [{speaker, text, emotion, power_move}]

        Returns:
            {
                "speaker_id": speaker_id,
                "speaker_result": CognitiveResult,
                "listener_updates": {listener_id: micro_update_result},
                "conversation_turn": {speaker, text, emotion, power_move}
            }
        """
        # 优先使用外置对话历史存储
        # 如果提供了外部store，忽略 conversation_history 参数
        if self.conversation_store is not None:
            history = self.conversation_store.get_recent_turns(10)
        else:
            history = conversation_history or []

        # 1. 为发言者准备增强上下文 — 包含倾听者信息
        speaker_cs = characters[speaker_id]
        enhanced_event = dict(shared_event)

        # 对话历史通过 _prepare_context 注入 external_history，不再塞进 event description
        # 这保持了每次 LLM 调用都是全新会话（base.py 中已是单条 user message）
        if history and not self.conversation_store:
            # 回退模式: 无外置存储时保持旧行为
            history_text = "\n".join(
                f"{h['speaker']}: {h['text']}" if isinstance(h, dict) else f"{h.speaker_id}: {h.text}"
                for h in history[-10:]
            )
            enhanced_event["description"] = (
                f"对话历史:\n{history_text}\n\n"
                f"现在轮到{speaker_id}说话。事件: {shared_event.get('description', '')}"
            )

        # 注入倾听者作为事件参与者
        enhanced_event["participants"] = [
            {"name": lid, "relation": self._infer_relation(characters, speaker_id, lid)}
            for lid in listener_ids
        ]

        # 2. 发言者运行完整认知管道
        speaker_result = await self.process_event(
            provider, speaker_cs, enhanced_event
        )

        # 3. 发言后 — 更新所有倾听者的状态机(micro_update)
        listener_updates = {}
        speaker_emotion = self._extract_dominant_emotion(speaker_result)
        speaker_power = self._classify_power_move(speaker_result, history)

        for lid in listener_ids:
            listener_cs = characters[lid]
            psm_data = listener_cs.get("personality_state_machine")
            if psm_data:
                psm = PersonalityStateMachine.from_dict(psm_data)
                update = psm.micro_update(
                    partner_emotion=speaker_emotion,
                    partner_power_move=speaker_power,
                    topic_keywords=shared_event.get("topic_keywords", []),
                )
                listener_cs["personality_state_machine"] = psm.to_dict()
                listener_updates[lid] = update

        # 4. 更新发言者自己的状态机（对话中的自我反馈）
        speaker_psm_data = speaker_cs.get("personality_state_machine")
        if speaker_psm_data:
            speaker_psm = PersonalityStateMachine.from_dict(speaker_psm_data)
            # 自我反馈：发言者的神经质微降（说出来了=释放了压力）
            speaker_psm.micro_update(
                partner_emotion={"dominant": "neutral", "intensity": 0.3},
                partner_power_move="neutral",
            )
            speaker_cs["personality_state_machine"] = speaker_psm.to_dict()

        # 5. 存储对话轮到共享事件记忆
        turn_record = {
            "speaker": speaker_id,
            "text": self._extract_response_text(speaker_result),
            "emotion": speaker_emotion,
            "power_move": speaker_power,
        }

        # 持久化到外置对话历史存储
        # 对话历史不进入API上下文窗口，只存储在外部
        if self.conversation_store is not None:
            speaker_label = characters[speaker_id].get("name", speaker_id)
            self.conversation_store.add_turn(ConversationTurn(
                timestamp=ConversationTurn.now_timestamp(),
                speaker_id=speaker_id,
                speaker_label=speaker_label,
                text=turn_record["text"],
                emotion=speaker_emotion,
                power_move=speaker_power,
            ))

        return {
            "speaker_id": speaker_id,
            "speaker_result": speaker_result,
            "listener_updates": listener_updates,
            "conversation_turn": turn_record,
        }

    @staticmethod
    def _extract_dominant_emotion(result: CognitiveResult) -> dict:
        """从CognitiveResult提取主导情绪"""
        l1 = result.layer_results.get(1, [])
        if l1 and l1[0].success:
            internal = l1[0].output.get("internal", {})
            return {
                "dominant": internal.get("dominant", "neutral"),
                "intensity": internal.get("intensity", 0.5),
                "pleasantness": internal.get("pleasantness", 0.0),
            }
        return {"dominant": "neutral", "intensity": 0.3, "pleasantness": 0.0}

    @staticmethod
    def _classify_power_move(result: CognitiveResult,
                             history: list) -> str:
        """从发言结果分类权力动作。history 可以是 dict 列表或 ConversationTurn 列表."""
        l3 = result.layer_results.get(3, [])
        if l3:
            for s in l3:
                if s.success:
                    discourse = s.output.get("discourse_position", "")
                    if discourse == "dominant":
                        return "dominate"
                    if discourse == "resisting":
                        return "threaten"

        # 从情绪推断
        emotion = CognitiveOrchestrator._extract_dominant_emotion(result)
        if emotion.get("dominant") in ("anger",):
            return "threaten"
        if emotion.get("dominant") in ("fear", "sadness"):
            return "submit"

        # 从历史推断：如果上一轮被对方支配，当前可能是appeal
        if history:
            last = history[-1]
            # 兼容 dict 和 ConversationTurn
            last_power = (
                last.get("power_move") if isinstance(last, dict)
                else getattr(last, "power_move", None)
            )
            if last_power == "dominate":
                return "appeal"

        return "neutral"

    @staticmethod
    def _infer_relation(characters: dict, speaker: str,
                        listener: str) -> str:
        """推断两个角色之间的关系."""
        speaker_cs = characters.get(speaker, {})
        relations = speaker_cs.get("relations", {})
        return relations.get(listener, "acquaintance")

    @staticmethod
    def _extract_response_text(result: CognitiveResult) -> str:
        """从CognitiveResult中提取角色的回应文本."""
        l5 = result.layer_results.get(5, [])
        if l5 and l5[0].success:
            text = l5[0].output.get("response_text", "")
            if text:
                return text
        # Fallback: 从state_changes中提取
        changes = result.state_changes
        if changes:
            return str(changes)
        return ""


def get_orchestrator(
    episodic_store: EpisodicMemoryStore | None = None,
    conversation_store: ConversationHistoryStore | None = None,
    anti_alignment_enabled: bool = True,
    biological_bridge=None,
) -> CognitiveOrchestrator:
    """创建一个新的编排器实例。每次调用返回独立实例，避免会话间状态泄漏。"""
    return CognitiveOrchestrator(
        episodic_store=episodic_store,
        conversation_store=conversation_store,
        anti_alignment_enabled=anti_alignment_enabled,
        biological_bridge=biological_bridge,
    )

