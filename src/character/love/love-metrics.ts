/**
 * Love Metrics — Assurance vs Confidence.
 * 1:1 translation from core/love/love_metrics.py
 *
 * Confidence = P(belief | evidence), Bayesian posterior. Evidence-dependent.
 * Assurance = non-probabilistic, will-based certainty. Not evidence-dependent.
 * "I will always be with you" is assurance, not a probability estimate.
 */
export class LoveMetrics {
  counterparty: string;
  oathRenewalFrequency: number;
  repairSuccessRate: number;
  relationshipDurationDays: number;
  presenceQuality: number;
  positiveRatio: number;
  ruptureCount: number;
  repairCount: number;
  depthSessions: number;

  constructor(counterparty: string = '') {
    this.counterparty = counterparty;
    this.oathRenewalFrequency = 0.5;
    this.repairSuccessRate = 0.5;
    this.relationshipDurationDays = 0;
    this.presenceQuality = 0.5;
    this.positiveRatio = 3.0;
    this.ruptureCount = 0;
    this.repairCount = 0;
    this.depthSessions = 0;
  }

  get assurance(): number {
    const renewalScore = this.oathRenewalFrequency;
    const repairScore = this.ruptureCount > 0
      ? this.repairCount / this.ruptureCount
      : 0.5;
    const durationScore = Math.min(1.0, Math.log(1 + this.relationshipDurationDays) / Math.log(366));
    const presenceScore = this.presenceQuality;

    const a = renewalScore * 0.35 + repairScore * 0.25 + durationScore * 0.15 + presenceScore * 0.25;
    return Math.round(Math.min(1.0, Math.max(0.0, a)) * 10000) / 10000;
  }

  get isHealthy(): boolean {
    return this.positiveRatio >= 3.0 && this.repairSuccessRate >= 0.5;
  }

  get gottmanStatus(): string {
    if (this.positiveRatio >= 5.0) return 'thriving';
    if (this.positiveRatio >= 3.0) return 'stable';
    if (this.positiveRatio >= 1.0) return 'at_risk';
    return 'critical';
  }

  recordPositive(): void { this.positiveRatio = Math.min(10, this.positiveRatio + 0.1); }
  recordNegative(): void { this.positiveRatio = Math.max(0.1, this.positiveRatio - 0.3); }
  recordRupture(): void { this.ruptureCount++; this.positiveRatio = Math.max(0.1, this.positiveRatio - 1.0); }
  recordRepair(): void { this.repairCount++; this.positiveRatio = Math.min(10, this.positiveRatio + 0.5); }
  recordDeepConnection(): void { this.depthSessions++; this.presenceQuality = Math.min(1.0, this.presenceQuality + 0.05); }
  recordOathRenewal(): void { this.oathRenewalFrequency = Math.min(1.0, this.oathRenewalFrequency + 0.1); }

  tick(dtDays: number): void {
    this.oathRenewalFrequency = Math.max(0, this.oathRenewalFrequency - 0.02 * dtDays);
    this.presenceQuality = Math.max(0.1, this.presenceQuality - 0.01 * dtDays);
    this.relationshipDurationDays += dtDays;
  }

  compare(confidence: number): Record<string, unknown> {
    const gap = Math.round((this.assurance - confidence) * 10000) / 10000;
    return {
      assurance: this.assurance,
      confidence: Math.round(confidence * 10000) / 10000,
      gap,
      interpretation: gap > 0.2 ? '誓约坚定，即使证据不足'
        : gap < -0.2 ? '证据充分，但誓约需要更新'
        : '认知和意志一致',
    };
  }

  toDict(): Record<string, unknown> {
    return {
      assurance: this.assurance,
      health: this.gottmanStatus,
      positiveRatio: Math.round(this.positiveRatio * 10) / 10,
      ruptures: this.ruptureCount,
      repairs: this.repairCount,
      depthSessions: this.depthSessions,
      durationDays: Math.round(this.relationshipDurationDays * 10) / 10,
    };
  }
}
