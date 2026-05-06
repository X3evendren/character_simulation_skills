from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math


@dataclass
class NeurotransmitterEngine:
    """5-neurotransmitter system with baselines, phasic/tonic dynamics, receptor adaptation."""

    # Half-lives in minutes
    HALF_LIVES = {"DA": 5.0, "5HT": 30.0, "NE": 10.0, "CORT": 90.0, "OXT": 15.0}
    # Receptor adaptation timescales in hours
    TAU_UP: float = 48.0   # upregulation
    TAU_DOWN: float = 24.0  # downregulation (faster than up)
    # Cross-NT interaction weights
    W_5HT_DA: float = 0.3   # 5-HT suppresses DA
    W_CORT_5HT: float = 0.4  # CORT suppresses 5-HT
    W_CORT_NE: float = 0.3   # CORT enhances NE
    W_NE_OXT: float = 0.3    # NE suppresses OXT

    def __init__(self):
        self.state = {}
        self.receptors = {}
        self.baselines = {}
        self._init_defaults()

    def _init_defaults(self):
        """Initialize with neutral defaults."""
        for nt in ["DA", "5HT", "NE", "CORT", "OXT"]:
            self.state[nt] = 0.5
            self.receptors[nt] = 0.5
            self.baselines[nt] = 0.5 if nt != "CORT" else 0.3

    def set_baselines_from_ocean(self, ocean: dict, attachment: str = "secure", ace: int = 0):
        """Set NT baselines from OCEAN personality traits.

        Evidence basis (Doya 2002, DeYoung 2010, 2024 meta-analyses):
        - Extraversion <-> DA (r ~ 0.4-0.6)
        - Neuroticism <-> 5-HT(-) + NE(+) (strongest GWAS signal)
        - Openness <-> DA (moderate)
        - Conscientiousness <-> 5-HT(+) + PFC DA/NE (weakest direct link)
        - Agreeableness <-> OXT(+) + 5-HT(+) (moderate)
        """
        E = ocean.get("extraversion", 0.5)
        N = ocean.get("neuroticism", 0.5)
        O = ocean.get("openness", 0.5)
        C = ocean.get("conscientiousness", 0.5)
        A = ocean.get("agreeableness", 0.5)

        # DA: Extraversion (0.6) + Openness (0.3)
        self.baselines["DA"] = self._clamp(E * 0.6 + O * 0.3 + 0.1)

        # 5-HT: (1-Neuroticism)*0.7 + Conscientiousness*0.2
        self.baselines["5HT"] = self._clamp((1.0 - N) * 0.7 + C * 0.2 + 0.1)

        # NE: Neuroticism*0.5 + Extraversion*0.2
        self.baselines["NE"] = self._clamp(N * 0.5 + E * 0.2 + 0.2)

        # CORT: ACE*0.4 + Neuroticism*0.3
        ace_norm = min(ace / 10.0, 1.0)
        self.baselines["CORT"] = self._clamp(ace_norm * 0.4 + N * 0.3 + 0.2)

        # OXT: Agreeableness*0.5 + attachment modulation
        attach_oxt = {"secure": 0.15, "anxious": 0.05, "avoidant": -0.15, "fearful_avoidant": -0.05}.get(attachment, 0.0)
        self.baselines["OXT"] = self._clamp(A * 0.5 + attach_oxt + 0.3)

        # Set current levels to baselines
        for nt in self.baselines:
            self.state[nt] = self.baselines[nt]

    def update(self, dt_minutes: float, events: list[dict] | None = None, drives: dict | None = None):
        """Update NT levels for one timestep.

        Args:
            dt_minutes: Time elapsed in minutes
            events: List of event dicts with 'type' and 'significance'
            drives: Dict of current drive states (for tonic modulation)
        """
        # 1. Phasic responses to events
        phasic: dict[str, float] = {"DA": 0.0, "5HT": 0.0, "NE": 0.0, "CORT": 0.0, "OXT": 0.0}
        if events:
            for evt in events:
                sig = evt.get("significance", 0.5)
                etype = evt.get("type", "")
                tags = evt.get("tags", [])

                # DA: reward, goal achievement, novelty
                if etype in ("triumph", "breakthrough", "romantic") or "reward" in tags:
                    phasic["DA"] += sig * 0.3
                # 5-HT: safety confirmation, fair treatment, rest
                if etype in ("routine", "social") or "safe" in tags:
                    phasic["5HT"] += sig * 0.15
                # NE: threat, novelty, task demand
                if etype in ("conflict", "threat", "battle") or "threat" in tags:
                    phasic["NE"] += sig * 0.4
                if "novel" in tags:
                    phasic["NE"] += sig * 0.2
                # OXT: social contact, trust, touch
                if etype in ("social", "romantic") or "social" in tags:
                    phasic["OXT"] += sig * 0.25
                # CORT: stress events (from HPA axis, not direct)
                if etype in ("trauma", "betrayal", "death", "conflict"):
                    phasic["CORT"] += sig * 0.1  # small direct effect, HPA handles rest

        # 2. Tonic modulation from drives
        tonic: dict[str, float] = {"DA": 0.0, "5HT": 0.0, "NE": 0.0, "CORT": 0.0, "OXT": 0.0}
        if drives:
            # Drive tension increases related NTs
            tonic["NE"] += drives.get("safety", 0) * 0.1
            tonic["NE"] += drives.get("novelty", 0) * 0.05
            tonic["CORT"] += drives.get("safety", 0) * 0.15
            tonic["CORT"] += drives.get("social", 0) * 0.05
            tonic["DA"] += drives.get("novelty", 0) * 0.1
            tonic["DA"] += drives.get("seeking", 0) * 0.15
            tonic["OXT"] -= drives.get("social", 0) * 0.1  # social deprivation lowers OXT

        # 3. Apply decay back to baseline
        for nt in ["DA", "5HT", "NE", "CORT", "OXT"]:
            tau = self.HALF_LIVES[nt] / math.log(2)  # convert half-life to time constant
            decay_rate = 1.0 - math.exp(-dt_minutes / tau) if dt_minutes > 0 else 0.0
            self.state[nt] += (self.baselines[nt] - self.state[nt]) * decay_rate
            self.state[nt] += (phasic[nt] + tonic[nt]) * (1.0 - decay_rate)
            self.state[nt] = self._clamp(self.state[nt])

        # 4. Receptor adaptation (slow)
        dt_hours = dt_minutes / 60.0
        for nt in ["DA", "5HT", "NE", "CORT", "OXT"]:
            # Downregulation from high NT
            down = self.state[nt] * self.receptors[nt] / self.TAU_DOWN * dt_hours
            # Upregulation to normal
            up = (0.5 - self.receptors[nt]) / self.TAU_UP * dt_hours
            self.receptors[nt] += up - down
            self.receptors[nt] = self._clamp(self.receptors[nt])

    def get_effective(self, nt: str) -> float:
        """Get effective NT level (raw * receptor sensitivity)."""
        return self._clamp(self.state.get(nt, 0.5) * (self.receptors.get(nt, 0.5) / 0.5))

    def get_modulation_params(self) -> dict[str, float]:
        """Compute parameters that modulate the cognitive pipeline.

        Based on Doya (2002) metalearning framework:
        DA -> reward learning rate
        5-HT -> discount factor (time horizon)
        NE -> exploration vs exploitation (inverse temperature)
        """
        da = self.get_effective("DA")
        ne = self.get_effective("NE")
        ht = self.get_effective("5HT")
        cort = self.get_effective("CORT")
        oxt = self.get_effective("OXT")

        return {
            "reward_learning_rate": da * 0.3 + 0.1,        # 0.1-0.4
            "discount_factor": ht * 0.4 + 0.3,              # 0.3-0.7
            "exploration_temperature": ne * 0.5 + 0.1,      # 0.1-0.6
            "threat_sensitivity": ne * 0.6 + cort * 0.3,    # 0-0.9
            "social_reward_weight": oxt * 0.7 + 0.15,       # 0.15-0.85
            "emotional_persistence": cort * 0.5 + 0.5,      # 0.5-1.0 (CORT slows decay)
            "impulse_control": ht * 0.5 + 0.2,              # 0.2-0.7
            "risk_aversion": cort * 0.4 + (1.0 - da) * 0.3, # 0-0.7
        }

    def _clamp(self, v: float) -> float:
        return max(0.0, min(1.0, v))
