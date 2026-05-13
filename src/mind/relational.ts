/**
 * Relational Layer — Saturation detection + Precision rerouting.
 * 
 *
 * S1 (ENCODE): Normal Bayesian update on the other-model
 * S2 (SATURATED): Reroute prediction error to update self-model
 */
export enum RelationMode {
  ENCODE = 'encode',
  TRANSITIONING = 'transitioning',
  SATURATED = 'saturated',
  RUPTURED = 'ruptured',
}

export class SaturationDetector {
  counterparty: string;
  convergenceWindow: number;
  errorThreshold: number;
  shiftThreshold: number;
  errorHistory: number[];
  selfModelHistory: number[];
  mode: RelationMode;
  saturationLevel: number;
  lastModeChange: number;

  constructor(counterparty: string = '') {
    this.counterparty = counterparty;
    this.convergenceWindow = 10;
    this.errorThreshold = 0.25;
    this.shiftThreshold = 0.08;
    this.errorHistory = [];
    this.selfModelHistory = [];
    this.mode = RelationMode.ENCODE;
    this.saturationLevel = 0;
    this.lastModeChange = 0;
  }

  observe(predictionError: number, selfModelShift: number): void {
    this.errorHistory.push(predictionError);
    this.selfModelHistory.push(selfModelShift);
    if (this.errorHistory.length > this.convergenceWindow)
      this.errorHistory = this.errorHistory.slice(-this.convergenceWindow);
    if (this.selfModelHistory.length > this.convergenceWindow)
      this.selfModelHistory = this.selfModelHistory.slice(-this.convergenceWindow);
  }

  evaluate(): RelationMode {
    if (this.errorHistory.length < 5) return RelationMode.ENCODE;

    const recentErrors = this.errorHistory.slice(-5);
    const meanError = recentErrors.reduce((a, b) => a + b, 0) / recentErrors.length;
    const errorTrend = SaturationDetector._trend(this.errorHistory);

    const recentShifts = this.selfModelHistory.length > 0
      ? this.selfModelHistory.slice(-5) : [0];
    const meanShift = recentShifts.reduce((a, b) => a + b, 0) / recentShifts.length;

    const isNonConverging = meanError > this.errorThreshold && errorTrend >= 0;
    const isSelfShifting = meanShift > this.shiftThreshold;

    if (this.mode === RelationMode.RUPTURED) return this.mode;

    if (isNonConverging && isSelfShifting) {
      if (this.mode === RelationMode.ENCODE) {
        this.mode = RelationMode.TRANSITIONING;
        this.lastModeChange = Date.now() / 1000;
      }
      if (this.mode === RelationMode.TRANSITIONING) {
        if (Date.now() / 1000 - this.lastModeChange > 30) {
          this.mode = RelationMode.SATURATED;
          this.lastModeChange = Date.now() / 1000;
        }
      }
    } else if (!isNonConverging) {
      if (this.mode === RelationMode.TRANSITIONING || this.mode === RelationMode.SATURATED) {
        this.mode = RelationMode.ENCODE;
        this.saturationLevel *= 0.7;
        this.lastModeChange = Date.now() / 1000;
      }
    }

    // Update continuous saturation level
    if (this.mode === RelationMode.SATURATED) {
      this.saturationLevel = Math.min(1.0, this.saturationLevel + 0.02);
    } else if (this.mode === RelationMode.ENCODE) {
      this.saturationLevel = Math.max(0, this.saturationLevel - 0.03);
    } else if (this.mode === RelationMode.TRANSITIONING) {
      this.saturationLevel = Math.min(0.7, this.saturationLevel + 0.01);
    }

    return this.mode;
  }

  rupture(): void {
    this.mode = RelationMode.RUPTURED;
    this.saturationLevel = Math.max(0.3, this.saturationLevel - 0.2);
    this.lastModeChange = Date.now() / 1000;
  }

  repair(): void {
    if (this.mode === RelationMode.RUPTURED) {
      this.mode = RelationMode.SATURATED;
      this.saturationLevel = Math.min(1.0, this.saturationLevel);
      this.lastModeChange = Date.now() / 1000;
    }
  }

  private static _trend(history: number[]): number {
    if (history.length < 3) return 0;
    const mid = Math.floor(history.length / 2);
    const first = history.slice(0, mid).reduce((a, b) => a + b, 0) / mid;
    const second = history.slice(mid).reduce((a, b) => a + b, 0) / (history.length - mid);
    return second - first;
  }

  toDict(): Record<string, unknown> {
    const recentErrors = this.errorHistory.slice(-5);
    const recentShifts = this.selfModelHistory.slice(-5);
    return {
      mode: this.mode,
      saturation: Math.round(this.saturationLevel * 1000) / 1000,
      meanError: recentErrors.length > 0
        ? Math.round(recentErrors.reduce((a, b) => a + b, 0) / recentErrors.length * 1000) / 1000
        : 0,
      meanShift: recentShifts.length > 0
        ? Math.round(recentShifts.reduce((a, b) => a + b, 0) / recentShifts.length * 1000) / 1000
        : 0,
    };
  }
}

export class PrecisionRouter {
  counterparty: string;
  piLove: number;

  constructor(counterparty: string = '') {
    this.counterparty = counterparty;
    this.piLove = 0.5;
  }

  get rerouteEnabled(): boolean {
    return this.piLove > 0.1;
  }

  route(predictionErrorOther: number, mode: RelationMode): [number, number] {
    if (mode === RelationMode.SATURATED) {
      return [0, this.piLove * predictionErrorOther];
    } else if (mode === RelationMode.RUPTURED) {
      return [0, 0];
    } else {
      return [predictionErrorOther, 0];
    }
  }

  toDict(): Record<string, unknown> {
    return {
      piLove: Math.round(this.piLove * 1000) / 1000,
      rerouteEnabled: this.rerouteEnabled,
    };
  }
}
