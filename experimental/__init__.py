"""实验性子系统 — 非默认运行图，独立于主认知管线。

连续意识流原型:
- TOCA / PerceptionStream / BehaviorStream: 连续意识流
- Blackboard: 版本化共享状态
- ConsciousnessLayer: GWT + HOT + 预测处理
- ThalamicGate / WmLtmBridge: 注意-记忆桥接

现象学Agent运行时:
- PhenomenologicalRuntime: 长运行守护进程
- InnerExperienceStream: 私有内部体验流
- ExpressionPolicy: 内部→外部表达转换
- WorldAdapter: OpenClaw风格通道/工具边界
- ExperienceAuditor: NLA风格内部状态审计
- SelfModel: 第一人称自我/他人/冲突模型
- ProceduralMemoryStore: 触发-预测-防御-回应规则
- OfflineConsolidation: 记忆重播与巩固

所有模块独立于 core 主管线运行，可单独启停。
"""
from .blackboard import Blackboard
from .perception_stream import PerceptionStream
from .behavior_stream import BehaviorStream
from .consciousness import ConsciousnessLayer
from .thalamic_gate import ThalamicGate
from .wm_ltm_bridge import WmLtmBridge
from .self_model import SelfModel
from .procedural_memory import ProceduralMemoryStore
from .offline_consolidation import OfflineConsolidation
from .toca_runner import TocaRunner, TocaConfig
from .inner_experience import InnerExperienceStream
from .expression_policy import ExpressionPolicy
from .world_adapter import WorldAdapter
from .experience_auditor import ExperienceAuditor
from .phenomenological_runtime import PhenomenologicalRuntime
