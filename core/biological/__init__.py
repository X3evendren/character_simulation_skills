from __future__ import annotations

from .biological_state import BiologicalState
from .neurotransmitter import NeurotransmitterEngine

# Optional imports — modules may be created later
try:
    from .drive_system import DriveSystem
except ImportError:
    DriveSystem = None  # type: ignore

try:
    from .hpa_axis import HPAAxis
except ImportError:
    HPAAxis = None  # type: ignore

try:
    from .active_inference import ActiveInferenceBridge
except ImportError:
    ActiveInferenceBridge = None  # type: ignore

try:
    from .biological_bridge import BiologicalBridge
except ImportError:
    BiologicalBridge = None  # type: ignore

__all__ = [
    "BiologicalState",
    "NeurotransmitterEngine",
    "DriveSystem",
    "HPAAxis",
    "ActiveInferenceBridge",
    "BiologicalBridge",
]
