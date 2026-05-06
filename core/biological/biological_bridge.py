"""Biological Bridge — 连接生物基础层与现有认知管道。

在 orchestrator.process_event() 前后调用，更新生物状态并注入认知上下文。
"""
from __future__ import annotations

from typing import Any
from .biological_state import BiologicalState
from .neurotransmitter import NeurotransmitterEngine
from .drive_system import DriveSystem
from .hpa_axis import HPAAxis
from .active_inference import ActiveInferenceBridge


class BiologicalBridge:
    """生物-认知桥接器。

    Usage:
        bridge = BiologicalBridge()
        bridge.set_character_profile(ocean, attachment, ace)
        bio_ctx = bridge.before_event(event, dt_seconds)
        result = await orchestrator.process_event(provider, character, event, bio_ctx)
        bridge.after_event(event, result)
    """

    def __init__(self):
        self.state = BiologicalState()
        self.nt_engine = NeurotransmitterEngine()
        self.drive_system = DriveSystem()  # 自带 DriveState
        self.hpa = HPAAxis()
        self.active_inference = ActiveInferenceBridge()
        self.last_update_time: float = 0.0

    def set_character_profile(self, ocean: dict, attachment: str = "secure", ace: int = 0):
        self.nt_engine.set_baselines_from_ocean(ocean, attachment, ace)
        self.hpa.set_trauma_params(ace)
        self.active_inference.set_prior_beliefs_from_personality(ocean, attachment, ace)

    def before_event(self, event: dict, dt_seconds: float) -> dict:
        dt_minutes = dt_seconds / 60.0
        self.state.timestamp += dt_seconds
        self.state.event_count += 1

        # 1. 驱力更新
        event_type = event.get("type", "routine")
        self.drive_system.update(dt_minutes, events=[{
            "type": event_type,
            "significance": event.get("significance", 0.5),
        }])

        # 2. HPA 轴
        stress = event.get("significance", 0.3) if event_type in (
            "trauma", "conflict", "betrayal", "threat") else 0.0
        hpa_state = self.hpa.update(dt_minutes, stress_input=stress)
        self.state.cortisol = hpa_state["cortisol"]
        self.state.CRH = hpa_state["CRH"]
        self.state.ACTH = hpa_state["ACTH"]
        self.state.GR = hpa_state["GR"]

        # 3. 递质引擎
        self.nt_engine.update(dt_minutes, events=[{
            "type": event_type,
            "significance": event.get("significance", 0.5),
            "tags": event.get("tags", []),
        }], drives=self.drive_system.state.get_drive_vector())
        for nt in ["DA", "5HT", "NE", "OXT"]:
            attr = nt if nt != "5HT" else "serotonin"
            setattr(self.state, attr, self.nt_engine.state.get(nt, 0.5))

        # 4. 主动推理桥接
        nt_vec = self.state.get_nt_vector()
        hpa_vec = {"cortisol": self.state.cortisol}
        precision_weights = self.active_inference.compute_precision_weights(nt_vec, hpa_vec)

        drives = self.drive_system.state.get_drive_vector()
        observations = {
            "safety": drives.get("safety", 0),
            "social": drives.get("social", 0),
            "autonomy": drives.get("autonomy", 0),
        }
        prediction_result = self.active_inference.compute_prediction_error(
            observations, precision_weights)
        action_tendency = self.active_inference.compute_action_tendency(
            drives, precision_weights)

        # 5. 构建上下文
        biological_context = self.active_inference.get_biological_context(
            drives, nt_vec, hpa_vec, precision_weights,
            prediction_result, action_tendency)
        modulation = self.nt_engine.get_modulation_params()
        biological_context["modulation"] = modulation

        self.state.prediction_surprise = prediction_result.get("total_surprise", 0.0)
        self.state.action_tendency = action_tendency
        self.last_update_time = self.state.timestamp

        return biological_context

    def after_event(self, event: dict, result: Any):
        response_text = ""
        if hasattr(result, "combined_analysis"):
            response_text = result.combined_analysis or ""
        if response_text and len(response_text) > 10:
            self.drive_system.update(0, actions=["talk"])

        etype = event.get("type", "")
        sig = event.get("significance", 0.5)
        # 事件后驱力调整已由 drive_system 处理，此处做额外精细调整
        if etype == "triumph":
            self.drive_system.update(0, actions=["achieve"])
        elif etype == "conflict":
            self.drive_system.update(0, actions=["defend"])

    def get_state_summary(self) -> dict:
        drives = self.drive_system.state.get_drive_vector()
        nt = self.state.get_nt_vector()
        urgent = {k: round(v, 2) for k, v in drives.items() if v > 0.5}
        return {
            "dominant_drive": max(drives, key=drives.get),
            "urgent_drives": urgent,
            "neurotransmitters": {k: round(v, 2) for k, v in nt.items()},
            "cortisol": round(self.state.cortisol, 2),
            "prediction_surprise": round(self.state.prediction_surprise, 3),
        }

    def to_dict(self) -> dict:
        return {
            "state": self.state.to_dict(),
            "hpa": self.hpa.to_dict(),
            "active_inference": self.active_inference.to_dict(),
            "drive_state": self.drive_system.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BiologicalBridge":
        bridge = cls()
        if "state" in d:
            bridge.state = BiologicalState.from_dict(d["state"])
        if "hpa" in d:
            bridge.hpa = HPAAxis.from_dict(d["hpa"])
        if "active_inference" in d:
            bridge.active_inference = ActiveInferenceBridge.from_dict(d["active_inference"])
        if "drive_state" in d:
            bridge.drive_system = DriveSystem.from_dict(d["drive_state"])
        return bridge
