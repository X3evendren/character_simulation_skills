/**
 * Oath Layer — Oath lifecycle manager.
 * 1:1 translation from core/love/oath_store.py
 *
 * An oath is not a prediction. It's a will-based constraint that excludes
 * future action space. In Bayesian terms, it structurally modifies the
 * utility function — excluded options no longer appear in the decision domain.
 */
export enum OathType {
  EXCLUSIVE = 'exclusive',
  CARE = 'care',
  FAITHFULNESS = 'faithfulness',
  PRESENCE = 'presence',
}

export enum OathState {
  DECLARED = 'declared',
  ACTIVE = 'active',
  LAPSING = 'lapsing',
  RENEWED = 'renewed',
  BROKEN = 'broken',
  REPAIRED = 'repaired',
}

export interface OathConstraint {
  excludedActions: string[];
  requiredActions: string[];
  overrideUtility: boolean;
}

export const defaultOathConstraint = (): OathConstraint => ({
  excludedActions: [],
  requiredActions: [],
  overrideUtility: true,
});

export interface OathEvent {
  timestamp: number;
  eventType: string;
  description: string;
  emotionalContext?: string;
}

export class Oath {
  id: string;
  counterparty: string;
  type: OathType;
  state: OathState;
  strength: number;
  renewedAt: number;
  decayRate: number;
  constraints: OathConstraint;
  renewalPeriodDays: number;
  history: OathEvent[];

  constructor(id: string, counterparty: string = '', type: OathType = OathType.EXCLUSIVE) {
    this.id = id;
    this.counterparty = counterparty;
    this.type = type;
    this.state = OathState.DECLARED;
    this.strength = 0.8;
    this.renewedAt = 0;
    this.decayRate = 0.05;
    this.constraints = defaultOathConstraint();
    this.renewalPeriodDays = 30;
    this.history = [];
  }

  declare(counterparty: string, oathType: OathType, constraints?: OathConstraint): void {
    this.counterparty = counterparty;
    this.type = oathType;
    this.state = OathState.DECLARED;
    this.strength = 0.8;
    this.renewedAt = Date.now() / 1000;
    if (constraints) this.constraints = constraints;
    this._log('declared', '首次宣誓');
  }

  renew(): void {
    const wasLapsing = this.state === OathState.LAPSING;
    this.state = wasLapsing ? OathState.RENEWED : OathState.ACTIVE;
    this.strength = Math.min(1.0, this.strength + 0.15);
    this.renewedAt = Date.now() / 1000;
    this._log('renewed', '重新确认誓约');
  }

  breach(description: string): void {
    this.state = OathState.BROKEN;
    this.strength = Math.max(0.1, this.strength - 0.4);
    this._log('breached', description);
  }

  repair(description: string): void {
    this.state = OathState.REPAIRED;
    this.strength = Math.min(1.0, this.strength + 0.2);
    this.renewedAt = Date.now() / 1000;
    this._log('repaired', description);
  }

  lapse(): void {
    if (this.state === OathState.ACTIVE) {
      this.state = OathState.LAPSING;
      this.strength = Math.max(0.2, this.strength - 0.15);
      this._log('lapsed', '超过确认周期未更新');
    }
  }

  terminate(): void {
    this.state = OathState.BROKEN;
    this.strength = 0;
    this._log('terminated', '誓约终止');
  }

  get isHardConstraint(): boolean {
    return [OathState.ACTIVE, OathState.RENEWED, OathState.REPAIRED].includes(this.state);
  }

  get isSoftConstraint(): boolean {
    return [OathState.DECLARED, OathState.LAPSING].includes(this.state);
  }

  get needsRenewal(): boolean {
    if (this.state === OathState.BROKEN) return false;
    const daysSince = (Date.now() / 1000 - this.renewedAt) / 86400;
    return daysSince > this.renewalPeriodDays;
  }

  checkViolation(action: string): boolean {
    return this.constraints.excludedActions.includes(action);
  }

  private _log(eventType: string, description: string): void {
    this.history.push({ timestamp: Date.now() / 1000, eventType, description });
    if (this.history.length > 100) this.history = this.history.slice(-100);
  }

  toDict(): Record<string, unknown> {
    return {
      id: this.id,
      counterparty: this.counterparty,
      type: this.type,
      state: this.state,
      strength: Math.round(this.strength * 1000) / 1000,
      renewedAt: this.renewedAt,
      isHard: this.isHardConstraint,
      history: this.history.slice(-10).map(e => ({
        t: e.timestamp,
        type: e.eventType,
        desc: e.description.slice(0, 80),
      })),
    };
  }
}

export class OathStore {
  private _oaths: Map<string, Oath> = new Map();
  private _byCounterparty: Map<string, string[]> = new Map();

  declare(counterparty: string, oathType: OathType, constraints?: OathConstraint): Oath {
    const oid = `oath_${counterparty}_${Math.floor(Date.now() / 1000)}`;
    const oath = new Oath(oid, counterparty, oathType);
    if (constraints) oath.constraints = constraints;
    oath.declare(counterparty, oathType, constraints);
    this._oaths.set(oid, oath);

    const existing = this._byCounterparty.get(counterparty) ?? [];
    existing.push(oid);
    this._byCounterparty.set(counterparty, existing);
    return oath;
  }

  getFor(counterparty: string): Oath[] {
    const ids = this._byCounterparty.get(counterparty) ?? [];
    return ids.map(id => this._oaths.get(id)!).filter(Boolean);
  }

  getActive(counterparty: string): Oath[] {
    return this.getFor(counterparty).filter(o => o.isHardConstraint);
  }

  getExcludedActions(counterparty: string): string[] {
    const actions: string[] = [];
    for (const oath of this.getActive(counterparty)) {
      actions.push(...oath.constraints.excludedActions);
    }
    return [...new Set(actions)];
  }

  tickAll(dtDays: number): void {
    for (const oath of this._oaths.values()) {
      if (oath.needsRenewal && oath.state === OathState.ACTIVE) {
        oath.lapse();
      }
      if (oath.state === OathState.LAPSING) {
        oath.strength = Math.max(0.1, oath.strength - oath.decayRate * dtDays);
      }
    }
  }

  allActive(): Oath[] {
    return [...this._oaths.values()].filter(o => o.isHardConstraint);
  }

  stats(): Record<string, number> {
    const all = [...this._oaths.values()];
    return {
      total: all.length,
      active: all.filter(o => o.isHardConstraint).length,
      lapsing: all.filter(o => o.state === OathState.LAPSING).length,
      broken: all.filter(o => o.state === OathState.BROKEN).length,
      repaired: all.filter(o => o.state === OathState.REPAIRED).length,
    };
  }
}
