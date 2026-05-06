from __future__ import annotations
import dataclasses
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BiologicalState:
    """Unified biological state container. Serializeable via to_dict/from_dict."""

    # Neurotransmitters (0-1 scale)
    DA: float = 0.5
    serotonin: float = 0.5
    NE: float = 0.5
    cortisol: float = 0.3
    oxytocin: float = 0.5

    # NT receptor sensitivities (0-1, 0.5=normal)
    DA_receptor: float = 0.5
    serotonin_receptor: float = 0.5
    NE_receptor: float = 0.5
    cortisol_receptor: float = 0.5
    oxytocin_receptor: float = 0.5

    # NT baselines (OCEAN-determined, 0-1)
    DA_baseline: float = 0.5
    serotonin_baseline: float = 0.5
    NE_baseline: float = 0.5
    cortisol_baseline: float = 0.3
    oxytocin_baseline: float = 0.5

    # HPA axis
    CRH: float = 0.3
    ACTH: float = 0.3
    GR: float = 1.0
    GR_total: float = 1.0

    # Drive states (15 drives, 0-1 where 0=satisfied, 1=critical)
    drive_energy: float = 0.3
    drive_safety: float = 0.2
    drive_rest: float = 0.4
    drive_social: float = 0.5
    drive_novelty: float = 0.6
    drive_competence: float = 0.3
    drive_autonomy: float = 0.2
    drive_comfort: float = 0.2
    drive_mating: float = 0.4
    drive_care: float = 0.3
    drive_status: float = 0.4
    drive_justice: float = 0.2
    drive_seeking: float = 0.5   # Panksepp SEEKING
    drive_play: float = 0.6      # Panksepp PLAY
    drive_panic: float = 0.1     # Panksepp PANIC

    # Active inference
    prediction_surprise: float = 0.0
    expected_free_energy: float = 0.0
    action_tendency: dict = field(default_factory=lambda: {
        "approach": 0.5, "withdraw": 0.1, "explore": 0.3, "exploit": 0.4
    })

    # Precision weights
    precision_reward: float = 0.5
    precision_threat: float = 0.5
    precision_social: float = 0.5
    precision_interoceptive: float = 0.5

    # Meta
    timestamp: float = 0.0
    event_count: int = 0

    def to_dict(self) -> dict:
        """Serialize all fields to dict for JSON/persistence."""
        from dataclasses import fields
        result = {}
        for f in fields(self):
            result[f.name] = getattr(self, f.name)
        return result

    @classmethod
    def from_dict(cls, d: dict) -> "BiologicalState":
        """Deserialize from dict."""
        valid_fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid_fields})

    def get_drive_vector(self) -> dict:
        """Return all 15 drives as a dict."""
        return {
            "energy": self.drive_energy, "safety": self.drive_safety,
            "rest": self.drive_rest, "social": self.drive_social,
            "novelty": self.drive_novelty, "competence": self.drive_competence,
            "autonomy": self.drive_autonomy, "comfort": self.drive_comfort,
            "mating": self.drive_mating, "care": self.drive_care,
            "status": self.drive_status, "justice": self.drive_justice,
            "seeking": self.drive_seeking, "play": self.drive_play,
            "panic": self.drive_panic,
        }

    def get_nt_vector(self) -> dict:
        """Return 5 NTs as a dict."""
        return {"DA": self.DA, "5HT": self.serotonin, "NE": self.NE,
                "CORT": self.cortisol, "OXT": self.oxytocin}

    def get_dominant_drive(self) -> str:
        """Return the name of the most urgent drive."""
        drives = self.get_drive_vector()
        return max(drives, key=drives.get)
