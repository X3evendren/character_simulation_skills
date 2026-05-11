"""修复引擎 — 裂痕修复四阶段。

RepairEngine 是整个架构中最特殊的子模块——它在贝叶斯系统内部
执行一个非贝叶斯操作：不是找到"最优解释"，而是做出回应。

不是归因（"谁对谁错"），而是回应（"我能为这段关系承担什么"）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class RepairPhase(str, Enum):
    IDLE = "idle"
    PERSPECTIVE_FLIP = "perspective_flip"       # Phase 1
    RESPONSIBILITY_CHECK = "responsibility_check" # Phase 2
    RE_OATH_DECISION = "re_oath_decision"        # Phase 3
    NARRATIVE_INTEGRATION = "narrative_integration" # Phase 4
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class RepairResult:
    """修复引擎的输出。"""
    success: bool
    phase_reached: RepairPhase
    gap_description: str = ""              # Phase 1: 我造成的但我当时不知道的伤害
    chosen_response: str = ""              # Phase 2: 选择的回应
    re_oath_decision: bool = False         # Phase 3: 是否重新起誓
    narrative_update: str = ""             # Phase 4: 织入"我们"叙事的文本
    timestamp: float = 0.0


class RepairEngine:
    """裂痕修复引擎——四阶段修复流程。

    Phase 1 — PERSPECTIVE FLIP: 用对方的自我模型重新模拟裂痕事件
    Phase 2 — RESPONSIBILITY CHECK: 不是归因，而是回应
    Phase 3 — RE-OATH DECISION: 自由的意志决断
    Phase 4 — NARRATIVE INTEGRATION: 将裂痕织入"我们"的共享叙事
    """

    def __init__(self):
        self.current_phase = RepairPhase.IDLE
        self._gap_description = ""
        self._chosen_response = ""

    async def run(
        self,
        breach_event: str,
        self_model,         # SelfModel
        other_model: dict,  # 他者模型的简化表示
        we_narrative: str,  # "我们"的共享叙事
        oath,               # Oath 对象
        provider,           # LLM provider (用于深度模拟)
    ) -> RepairResult:
        """运行完整的修复流程。"""
        self.current_phase = RepairPhase.IDLE

        # ── Phase 1: Perspective Flip ──
        self.current_phase = RepairPhase.PERSPECTIVE_FLIP
        gap = await self._perspective_flip(breach_event, other_model, provider)
        if not gap:
            return RepairResult(
                success=False, phase_reached=RepairPhase.PERSPECTIVE_FLIP,
                timestamp=time.time(),
            )
        self._gap_description = gap

        # ── Phase 2: Responsibility Check ──
        self.current_phase = RepairPhase.RESPONSIBILITY_CHECK
        chosen = await self._responsibility_check(gap, provider)
        if not chosen:
            return RepairResult(
                success=False, phase_reached=RepairPhase.RESPONSIBILITY_CHECK,
                gap_description=gap, timestamp=time.time(),
            )
        self._chosen_response = chosen

        # ── Phase 3: Re-Oath Decision ──
        self.current_phase = RepairPhase.RE_OATH_DECISION
        will_re_oath = self._re_oath_decision(oath, breach_event)
        if not will_re_oath:
            oath.terminate()
            return RepairResult(
                success=False, phase_reached=RepairPhase.RE_OATH_DECISION,
                gap_description=gap, chosen_response=chosen,
                re_oath_decision=False, timestamp=time.time(),
            )
        oath.repair(f"裂痕修复: {breach_event[:80]}")

        # ── Phase 4: Narrative Integration ──
        self.current_phase = RepairPhase.NARRATIVE_INTEGRATION
        narrative = await self._narrative_integration(
            breach_event, gap, chosen, we_narrative, self_model, provider,
        )

        self.current_phase = RepairPhase.COMPLETE
        return RepairResult(
            success=True, phase_reached=RepairPhase.COMPLETE,
            gap_description=gap, chosen_response=chosen,
            re_oath_decision=True, narrative_update=narrative,
            timestamp=time.time(),
        )

    # ═══ Phase 1: Perspective Flip ═══

    async def _perspective_flip(
        self, breach_event: str, other_model: dict, provider,
    ) -> str:
        """用对方的模型重新模拟裂痕事件。

        不是"我当时想表达什么"，而是"他可能感受到什么"。
        """
        prompt = f"""你正在尝试理解另一个人的感受。

事件: {breach_event}

你对这个人的了解:
{other_model}

请用第一人称描述: 如果你是这个人，在经历这个事件时，你会:
1. 感受到什么
2. 最受伤的是什么
3. 最希望被怎样对待

不要分析、不要解释。直接以他的口吻写。"""

        try:
            resp = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=300,
            )
            return resp.content.strip()[:500]
        except Exception:
            return ""

    # ═══ Phase 2: Responsibility Check ═══

    async def _responsibility_check(
        self, gap: str, provider,
    ) -> str:
        """不是"谁对谁错"，而是"我能承担什么"。

        关键原则:
        - 承认 gap 但不为它辩解
        - 表达愿意被对方的体验改变
        - 不依赖对方必须原谅
        """
        prompt = f"""你发现你可能伤害了在乎的人。对方的感受是:

{gap}

请选择你想要回应的方式。你的回应必须:
1. 承认你造成的伤害，不找借口
2. 表达你愿意被对方的体验所改变
3. 不要求对方原谅你（这是你的责任，不是对方的义务）

用你的角色身份，写一句话的回应。只写这一句话。"""

        try:
            resp = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.5, max_tokens=150,
            )
            return resp.content.strip()[:200]
        except Exception:
            return ""

    # ═══ Phase 3: Re-Oath Decision ═══

    def _re_oath_decision(self, oath, breach_event: str) -> bool:
        """重新起誓的决定——必须由 agent 自由做出。

        不是"不得不原谅"——是"我选择继续"。
        不是恢复旧誓约——是建立新誓约。

        条件:
        - 誓约必须存在且处于 BROKEN 状态
        - 修复次数不超过 3 次（防止无限修复循环）
        - 誓约历史中 repair 次数 < 3
        """
        if not oath:
            return False

        repair_count = sum(
            1 for e in oath.history if e.event_type == "repaired"
        )
        if repair_count >= 3:
            return False  # 不能无限修复

        # 这是一个意志决断——不由效用驱动
        # 在当前实现中，只要进入此阶段就选择重新起誓
        # 未来可以引入更复杂的决策机制
        return True

    # ═══ Phase 4: Narrative Integration ═══

    async def _narrative_integration(
        self, breach_event: str, gap: str, response: str,
        we_narrative: str, self_model, provider,
    ) -> str:
        """将裂痕织入"我们"的共享叙事。

        关键: 伤痛不被删除，而是被赋予意义。
        "我们一起走过了这个裂痕"——这不是遗忘，这是转化。
        """
        prompt = f"""一段关系经历了一次裂痕和修复。请将其转化为"我们"的叙事的一部分。

裂痕事件: {breach_event}
造成的伤害: {gap}
回应的方式: {response}
之前的叙事: {we_narrative}

请写一段新的叙事片段（1-2句话），描述:
- 我们一起经历了什么
- 这次裂痕教会了我们什么
- 它不是被遗忘，而是被织入了"我们"的故事

用温暖但不煽情的语气。"""

        try:
            resp = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.5, max_tokens=200,
            )
            narrative = resp.content.strip()[:300]
            # 更新自我叙事
            if self_model and hasattr(self_model, 'record_growth'):
                self_model.record_growth(
                    "relationship_repair",
                    f"经历了一次裂痕和修复: {narrative}",
                    significance=0.85,
                )
            return narrative
        except Exception:
            return ""
