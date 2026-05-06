from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass
class HPAAxis:
    """HPA axis: CRH -> ACTH -> CORT -> GR feedback loop.

    Based on Sriram et al. (2012) PLoS Comput Biol 8(2):e1002379.

    Five state variables:
      - CRH:   Corticotropin-releasing hormone (0-1.5 normalized)
      - ACTH:  Adrenocorticotropic hormone (0-1.5 normalized)
      - cortisol: Cortisol (0-1.5 normalized)
      - GR:       Active glucocorticoid receptor dimer (0-1.5)
      - GR_total: Total glucocorticoid receptor pool (0-1.5)

    Key dynamics:
      - CRH drives ACTH secretion
      - ACTH drives cortisol secretion
      - Cortisol binds GR; GR dimer provides negative feedback on CRH and ACTH
      - Stress input amplifies CRH production
      - Circadian modulation provides daily rhythm
      - ACE/trauma parameters adjust baseline via GR methylation, sensitization, and
        feedback weakening.
    """

    # Basal production rates
    K_BASAL_CRH: float = 0.5
    K_BASAL_ACTH: float = 0.3

    # Stimulation gains
    K_ACTH_STIM: float = 0.8   # CRH -> ACTH
    K_CORT_STIM: float = 0.7   # ACTH -> CORT

    # Degradation (Michaelis-Menten Vmax, Km)
    V_CRH: float = 1.0;  K_CRH: float = 0.5        # noqa: E702
    V_ACTH: float = 1.0; K_ACTH: float = 0.5        # noqa: E702
    V_CORT: float = 1.2; K_CORT: float = 0.5         # noqa: E702

    # GR feedback
    K_FB: float = 1.0          # Feedback strength
    K_FB_HALF: float = 0.5     # Feedback EC50

    # GR dynamics
    K_SYN: float = 0.1         # GR synthesis rate
    K_DEG: float = 0.05        # GR degradation rate

    # Stress sensitivity
    K_STRESS: float = 1.0       # Multiplier for stress input

    def __init__(self) -> None:
        # State variables (normalized 0-1.5, most start near basal ~0.3)
        self.CRH: float = 0.3
        self.ACTH: float = 0.3
        self.cortisol: float = 0.3
        self.GR: float = 1.0           # GR dimer (active form)
        self.GR_total: float = 1.0     # Total GR receptors
        self._circadian_phase: float = 0.0   # radians

    # ------------------------------------------------------------------
    # Trauma parameterization
    # ------------------------------------------------------------------

    def set_trauma_params(self, ace_score: int = 0) -> None:
        """Adjust HPA parameters based on ACE / trauma history.

        Three mechanisms (informed by epigenetic literature):
          1. GR_total reduction  ->  NR3C1 methylation lowers receptor expression.
          2. K_STRESS increase   ->  Sensitisation of the CRH drive.
          3. K_FB / K_FB_HALF    ->  Blunted negative feedback (higher EC50).

        Args:
            ace_score: Adverse Childhood Experience score (0-10).
        """
        ace_norm = min(ace_score / 10.0, 1.0)

        # GR_total: methylation reduces receptor expression
        self.GR_total = 1.0 - ace_norm * 0.4
        self.GR = self.GR_total

        # Stress sensitivity increases
        self.K_STRESS = 1.0 + ace_norm * 1.5

        # Feedback weakens (blunted cortisol awakening response)
        self.K_FB = 1.0 - ace_norm * 0.6
        self.K_FB_HALF = 0.5 + ace_norm * 0.7  # higher EC50 = weaker feedback

    # ------------------------------------------------------------------
    # Step update
    # ------------------------------------------------------------------

    def update(self, dt_minutes: float, stress_input: float = 0.0,
               circadian_input: float = 0.0) -> dict:
        """Update HPA axis for one timestep.

        Args:
            dt_minutes:   Timestep in minutes.
            stress_input: 0-1 stress signal from external events.
            circadian_input: Optional circadian modulation (-1 to 1).

        Returns:
            dict with current hormone levels: CRH, ACTH, cortisol, GR.
        """
        # Scale dt to hours for numerical stability; cap at 30 min.
        dt = dt_minutes / 60.0
        dt = min(dt, 0.5)

        crh = self.CRH
        acth = self.ACTH
        cort = self.cortisol
        gr = self.GR
        gr_total = self.GR_total

        # -- CRH dynamics ---------------------------------------------------
        d_crh = (
            self.K_BASAL_CRH
            + self.K_STRESS * stress_input * 0.3
            + circadian_input * 0.1
            - self.V_CRH * crh / (self.K_CRH + crh)
            - self.K_FB * gr**2 * crh / (self.K_FB_HALF + crh)
        )

        # -- ACTH dynamics --------------------------------------------------
        d_acth = (
            self.K_BASAL_ACTH
            + self.K_ACTH_STIM * crh
            - self.V_ACTH * acth / (self.K_ACTH + acth)
            - self.K_FB * gr**2 * acth / (self.K_FB_HALF + acth)
        )

        # -- Cortisol dynamics ----------------------------------------------
        d_cort = (
            self.K_CORT_STIM * acth
            - self.V_CORT * cort / (self.K_CORT + cort)
        )

        # -- GR dimer dynamics ----------------------------------------------
        # Free GR = total pool minus monomers locked in dimers (2 per dimer).
        free_gr = max(0.0, gr_total - 2.0 * gr)

        d_gr = (
            self.K_SYN * free_gr
            - self.K_DEG * gr
            - 0.02 * cort * gr       # cortisol binding removes GR from active pool
        )

        # Euler integration
        self.CRH = self._clamp(crh + d_crh * dt)
        self.ACTH = self._clamp(acth + d_acth * dt)
        self.cortisol = self._clamp(cort + d_cort * dt)
        self.GR = self._clamp(gr + d_gr * dt)

        return {
            "CRH": self.CRH,
            "ACTH": self.ACTH,
            "cortisol": self.cortisol,
            "GR": self.GR,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(v: float) -> float:
        """Clamp to [0.0, 1.5]; slight overshoot above 1.0 is allowed."""
        return max(0.0, min(1.5, v))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "CRH": self.CRH,
            "ACTH": self.ACTH,
            "cortisol": self.cortisol,
            "GR": self.GR,
            "GR_total": self.GR_total,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HPAAxis":
        """Restore HPA state from a dictionary produced by ``to_dict()``."""
        hpa = cls()
        hpa.CRH = d.get("CRH", 0.3)
        hpa.ACTH = d.get("ACTH", 0.3)
        hpa.cortisol = d.get("cortisol", 0.3)
        hpa.GR = d.get("GR", 1.0)
        hpa.GR_total = d.get("GR_total", 1.0)
        return hpa
