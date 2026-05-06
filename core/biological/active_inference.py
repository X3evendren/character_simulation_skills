"""Active inference bridge between biological states and cognitive pipeline.

Conventions
-----------
- Drive states (0-1) represent deficits / needs.
- NT levels (0-1) represent normalised neurotransmitter concentrations.
- Beliefs (0-1) represent prior probabilities about hidden states.
- Precision weights (0-1) represent inverse variance (1 = high certainty).
"""

from __future__ import annotations
import math
from typing import Any


# Default priors — used when no observation is available for a channel.
_DEFAULT_BELIEFS: dict[str, float] = {
    "safety": 0.7,
    "social_acceptance": 0.6,
    "competence": 0.6,
    "control": 0.5,
    "predictability": 0.5,
}


class ActiveInferenceBridge:
    """Bridge between biological states and the cognitive pipeline.

    Responsibilities
    ----------------
    - Convert drive states into prior preferences.
    - Convert NT / hormone levels into precision weights (attention allocation).
    - Compute prediction errors and update beliefs.
    - Compute action tendencies from expected free energy.

    The resulting ``biological_context`` dict is injected into the L0-L5 pipeline
    at each cognitive update cycle, allowing downstream skills to modulate their
    behaviour based on interoceptive / neurochemical state.
    """

    def __init__(self) -> None:
        self.beliefs: dict[str, float] = dict(_DEFAULT_BELIEFS)
        self.prediction_errors: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Prior belief configuration
    # ------------------------------------------------------------------

    def set_prior_beliefs_from_personality(
        self,
        ocean: dict,
        attachment: str = "secure",
        ace: int = 0,
    ) -> None:
        """Set prior beliefs based on personality and developmental history.

        Args:
            ocean: Dict with keys ``neuroticism``, ``extraversion``,
                   ``agreeableness``, ``conscientiousness`` (0-1).
            attachment: One of ``secure``, ``anxious``, ``avoidant``,
                        ``fearful_avoidant``.
            ace: Adverse Childhood Experience score (0-10).
        """
        N = ocean.get("neuroticism", 0.5)
        E = ocean.get("extraversion", 0.5)
        A = ocean.get("agreeableness", 0.5)
        C = ocean.get("conscientiousness", 0.5)
        ace_norm = min(ace / 10.0, 1.0)

        # Neuroticism & ACE -> lower safety / social priors
        self.beliefs["safety"] = 0.7 - N * 0.3 - ace_norm * 0.2
        self.beliefs["social_acceptance"] = 0.6 - N * 0.2 + E * 0.1

        # Attachment style -> social prior offset
        attach_adj = {
            "secure": 0.1,
            "anxious": -0.1,
            "avoidant": -0.2,
            "fearful_avoidant": -0.25,
        }
        self.beliefs["social_acceptance"] += attach_adj.get(attachment, 0.0)

        # Conscientiousness -> control prior
        self.beliefs["control"] = 0.5 + C * 0.2 - N * 0.15

        # Clamp all beliefs to [0.05, 0.95]
        for k in self.beliefs:
            self.beliefs[k] = max(0.05, min(0.95, self.beliefs[k]))

    # ------------------------------------------------------------------
    # Precision (inverse variance) computation
    # ------------------------------------------------------------------

    def compute_precision_weights(self, nt_state: dict,
                                  hpa_state: dict) -> dict:
        """Compute precision weights from neurotransmitter and HPA state.

        High precision  =  "this signal is reliable, trust it"
        Low precision   =  "this signal is noisy, down-weight it"

        References
        ----------
        Feldman & Friston (2010), *NeuroImage*.
        Seth & Critchley (2013), *Trends Cogn Sci*.

        Args:
            nt_state:  Neurotransmitter levels dict (DA, NE, 5HT, OXT, ...).
            hpa_state: HPA axis state dict (cortisol, ...).

        Returns:
            Precision weights for five channels:
            ``reward``, ``threat``, ``social``, ``interoceptive``, ``sensory``.
        """
        da = nt_state.get("DA", 0.5)
        ne = nt_state.get("NE", 0.5)
        ht = nt_state.get("5HT", 0.5)
        cort = hpa_state.get("cortisol", nt_state.get("CORT", 0.3))
        oxt = nt_state.get("OXT", 0.5)

        # Reward precision = DA-modulated
        precision_reward = da * 0.7 + 0.15

        # Threat precision = NE-modulated, amplified by CORT
        precision_threat = ne * 0.5 + cort * 0.4

        # Social precision = OXT-modulated, suppressed by CORT
        precision_social = oxt * 0.6 - cort * 0.2 + 0.2

        # Interoceptive precision = how "loud" body signals are (sigmoid)
        precision_interoceptive = 1.0 / (1.0 + math.exp(-5.0 * (ne + cort - 1.0)))

        # Sensory precision (inversely related to interoceptive)
        precision_sensory = 1.0 - precision_interoceptive * 0.5

        return {
            "reward": self._clamp(precision_reward),
            "threat": self._clamp(precision_threat),
            "social": self._clamp(precision_social),
            "interoceptive": self._clamp(precision_interoceptive),
            "sensory": self._clamp(precision_sensory),
        }

    # ------------------------------------------------------------------
    # Prediction error
    # ------------------------------------------------------------------

    def compute_prediction_error(self, observation: dict,
                                 precision_weights: dict) -> dict:
        """Compute precision-weighted prediction errors.

        For each observed channel the bridge computes::

            error = (actual - expected) * precision

        and updates the corresponding belief via a small learning step.

        Args:
            observation: Current state observations.  Expected keys (all 0-1):
                         ``safety``, ``social``, ``autonomy``.
            precision_weights: Output of ``compute_precision_weights``.

        Returns:
            Dict with keys ``errors`` (per-channel), ``total_surprise``,
            ``updated_beliefs``.
        """
        errors: dict[str, float] = {}

        # Safety prediction error
        if "safety" in observation:
            expected = self.beliefs.get("safety", 0.7)
            actual = 1.0 - observation["safety"]
            errors["safety"] = (actual - expected) * precision_weights.get("threat", 0.5)
            self.beliefs["safety"] += errors["safety"] * 0.1

        # Social prediction error
        if "social" in observation:
            expected = self.beliefs.get("social_acceptance", 0.6)
            actual = 1.0 - observation["social"]
            errors["social"] = (actual - expected) * precision_weights.get("social", 0.5)
            self.beliefs["social_acceptance"] += errors["social"] * 0.1

        # Control / autonomy prediction error
        if "autonomy" in observation:
            expected = self.beliefs.get("control", 0.5)
            actual = 1.0 - observation["autonomy"]
            errors["control"] = (actual - expected) * precision_weights.get("reward", 0.5)
            self.beliefs["control"] += errors["control"] * 0.1

        # Clamp beliefs after update
        for k in self.beliefs:
            self.beliefs[k] = max(0.05, min(0.95, self.beliefs[k]))

        total_surprise = sum(abs(e) for e in errors.values()) / max(len(errors), 1)
        self.prediction_errors = errors

        return {
            "errors": errors,
            "total_surprise": total_surprise,
            "updated_beliefs": dict(self.beliefs),
        }

    # ------------------------------------------------------------------
    # Action tendency (expected free energy)
    # ------------------------------------------------------------------

    def compute_action_tendency(self, drive_state: dict,
                                precision_weights: dict) -> dict:
        """Compute action tendencies from expected free energy.

        Two components:
          - **Instrumental value**: approach what satisfies urgent drives,
            withdraw from threats.
          - **Epistemic value**: explore to reduce uncertainty.

        Returns a softmax-normalised probability distribution over four
        action classes: ``approach``, ``withdraw``, ``explore``, ``exploit``.

        Args:
            drive_state:     Drive levels dict (safety, social, novelty, ...).
            precision_weights: Output of ``compute_precision_weights``.

        Returns:
            Dict mapping action class -> normalised weight (sums to 1).
        """
        drives = drive_state

        # Instrumental: approach
        approach_weight = (
            drives.get("social", 0.0) * 0.3
            + drives.get("novelty", 0.0) * 0.2
            + drives.get("mating", 0.0) * 0.2
            + drives.get("seeking", 0.0) * 0.3
        ) * precision_weights.get("reward", 0.5)

        # Instrumental: withdraw
        withdraw_weight = (
            drives.get("safety", 0.0) * 0.5
            + drives.get("panic", 0.0) * 0.4
        ) * precision_weights.get("threat", 0.5)

        # Epistemic: explore to reduce uncertainty
        explore_weight = (
            drives.get("novelty", 0.0) * 0.4
            + drives.get("seeking", 0.0) * 0.5
            + (1.0 - precision_weights.get("sensory", 0.5)) * 0.3
        )

        # Exploit: use known strategies
        exploit_weight = precision_weights.get("reward", 0.5) * 0.6

        raw = {
            "approach": approach_weight,
            "withdraw": withdraw_weight,
            "explore": explore_weight,
            "exploit": exploit_weight,
        }
        total = sum(raw.values()) + 0.001
        return {k: v / total for k, v in raw.items()}

    # ------------------------------------------------------------------
    # Biological context assembly
    # ------------------------------------------------------------------

    def get_biological_context(
        self,
        drive_state: dict,
        nt_state: dict,
        hpa_state: dict,
        precision_weights: dict,
        prediction_result: dict,
        action_tendency: dict,
    ) -> dict:
        """Assemble the ``biological_context`` dict for the cognitive pipeline.

        This is the primary output of the bridge; it is designed to be injected
        into the orchestrator's shared state so that downstream skills can read
        and react to the character's biological state.

        Args:
            drive_state:        Current drive levels.
            nt_state:           Current neurotransmitter levels.
            hpa_state:          Current HPA axis state.
            precision_weights:  Output of ``compute_precision_weights``.
            prediction_result:  Output of ``compute_prediction_error``.
            action_tendency:    Output of ``compute_action_tendency``.

        Returns:
            Dict structured for pipeline injection.
        """
        return {
            "drives": drive_state,
            "dominant_drive": max(drive_state, key=drive_state.get)  # type: ignore[arg-type]
            if drive_state else "none",
            "neurotransmitters": nt_state,
            "hpa": hpa_state,
            "precision_weights": precision_weights,
            "prediction_surprise": prediction_result.get("total_surprise", 0.0),
            "prediction_errors": prediction_result.get("errors", {}),
            "beliefs": prediction_result.get("updated_beliefs", {}),
            "action_tendency": action_tendency,
            "modulation": {
                "emotional_intensity_boost": (
                    prediction_result.get("total_surprise", 0.0) * 0.5
                ),
                "attention_focus": (
                    "threat"
                    if precision_weights.get("threat", 0.0) > 0.6
                    else "social"
                    if precision_weights.get("social", 0.0) > 0.6
                    else "neutral"
                ),
                "exploration_bias": action_tendency.get("explore", 0.3),
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clamp(self, v: float) -> float:
        """Clamp to [0.0, 1.0]."""
        return max(0.0, min(1.0, v))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "beliefs": dict(self.beliefs),
            "prediction_errors": dict(self.prediction_errors),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ActiveInferenceBridge":
        """Restore from a dictionary produced by ``to_dict()``."""
        bridge = cls()
        if "beliefs" in d:
            bridge.beliefs = dict(d["beliefs"])
        if "prediction_errors" in d:
            bridge.prediction_errors = dict(d["prediction_errors"])
        return bridge
