"""已归档模块 — 原 TocaRunner 生态系统。

这些模块在生产流程 (CharacterMind v2 + PhenomenologicalRuntime) 中不再使用。
仅保留用于测试的向后兼容。

归档原因: TocaRunner 架构被 PhenomenologicalRuntime 取代。
"""
from .toca_runner import TocaRunner, TocaConfig
from .offline_consolidation import OfflineConsolidation
from .wm_ltm_bridge import WmLtmBridge
from .procedural_memory import ProceduralMemoryStore
from .self_model import SelfModel
from .experience_auditor import ExperienceAuditor
