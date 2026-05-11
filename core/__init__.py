"""Character Mind v3 — 核心模块。"""
from .provider import OpenAIProvider, LLMResponse, ToolCallRequest, ToolResult
from .json_parser import extract_json, extract_xml, extract_xml_attr
from .fsm import FiniteStateMachine, State, FSMContext
from .mind_state import MindState
from .session import Session
from .learning import SkillLibrary, FeedbackLoop, SelfReflection, RLInterface
from .continuous_engine import SaturationState, ContinuousParams, detect_behavior_mode
from .private_space import PrivateSpace, Workspace
from .params import UnifiedParams, Param, ChangeSpeed
from .params_modulator import ParamsModulator, ModulationRecord
from .love import OathStore, Oath, OathType, OathState, SaturationDetector, PrecisionRouter, RelationMode, IrreduciblePrior, RepairEngine, LoveMetrics
