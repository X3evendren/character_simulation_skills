/**
 * Irreducible Prior — Meta-prior that forbids posterior collapse.
 * 1:1 translation from core/love/irreducible_prior.py
 *
 * Constraint: KL[q(s_beloved) || P(s_beloved | all_data)] > delta_min
 * Normal Bayesian learning shrinks posterior variance with more data.
 * This prior forces a lower bound on variance — a structural "you can never fully understand him".
 */
export class IrreduciblePrior {
  counterparty: string;
  deltaMin: number;      // KL lower bound
  gamma: number;          // Entropy reward coefficient (0=S1, >0=S2)
  currentKL: number;
  entropyEstimate: number;
  lastCheck: number;
  violationCount: number;

  constructor(counterparty: string = '') {
    this.counterparty = counterparty;
    this.deltaMin = 0.15;
    this.gamma = 0;
    this.currentKL = 1.0;
    this.entropyEstimate = 1.0;
    this.lastCheck = 0;
    this.violationCount = 0;
  }

  /** Check if the beloved model is over-converging. Returns true if prior is triggered. */
  checkConvergence(beliefEntropy: number): boolean {
    this.entropyEstimate = beliefEntropy;
    this.lastCheck = Date.now() / 1000;

    // Map entropy to KL estimate: high entropy = far from convergence = safe
    this.currentKL = Math.max(0.01, beliefEntropy);

    if (this.currentKL < this.deltaMin) {
      this.violationCount++;
      return true;
    }
    return false;
  }

  activate(gamma: number = 0.3): void {
    this.gamma = gamma;
  }

  deactivate(): void {
    this.gamma = 0;
    this.violationCount = 0;
  }

  get isActive(): boolean {
    return this.gamma > 0;
  }

  /** Modify free energy: F' = F_base - gamma * H[q(s_beloved)].
   *  Standard free energy requires entropy to be eliminated.
   *  Here -gamma*H explicitly rewards maintaining uncertainty.
   *  This is anti-Friston — but necessary in love.
   */
  modifyFreeEnergy(baseFreeEnergy: number, beliefEntropy: number): number {
    if (!this.isActive) return baseFreeEnergy;
    return baseFreeEnergy - this.gamma * beliefEntropy;
  }

  /** Constrain the beloved model's precision from over-determining. */
  modifyPrecisionUpdate(precision: number): number {
    if (!this.isActive) return precision;
    const maxPrecision = 1.0 / (this.deltaMin + 0.01);
    return Math.min(precision, maxPrecision);
  }

  toDict(): Record<string, unknown> {
    return {
      counterparty: this.counterparty,
      deltaMin: this.deltaMin,
      gamma: this.gamma,
      currentKL: Math.round(this.currentKL * 10000) / 10000,
      entropy: Math.round(this.entropyEstimate * 10000) / 10000,
      isActive: this.isActive,
      violations: this.violationCount,
    };
  }
}
