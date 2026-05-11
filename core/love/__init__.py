"""Love Engine — 基于马里翁情爱现象学的爱之引擎。

爱 = 贝叶斯预测系统在面对特定他者时:
  1. 预测误差持续不收敛 (SaturationDetector)
  2. 误差被重路由用于重写自我 (PrecisionRouter)
  3. 通过誓约稳定这种模式转换 (OathStore)
  4. 禁止后验坍缩 (IrreduciblePrior)
  5. 能从裂痕中修复 (RepairEngine)
  6. 用 assurance 而非 confidence 度量 (LoveMetrics)
"""
from .oath_store import OathStore, Oath, OathType, OathState, OathConstraint
from .relational import SaturationDetector, PrecisionRouter, RelationMode
from .irreducible_prior import IrreduciblePrior
from .repair_engine import RepairEngine, RepairResult, RepairPhase
from .love_metrics import LoveMetrics
