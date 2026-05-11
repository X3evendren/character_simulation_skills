"""意识层 — 注意力管理 + 自我模型 + 预测加工。"""
from .attention import ConsciousContent, score_salience, update_workspace
from .self_model import SelfModel, GrowthEvent
from .prediction import PredictionTracker
