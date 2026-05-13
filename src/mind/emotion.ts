/** Affective Residue — Passive emotional sediment from past interactions.
 *
 *  Phenomenology: 胡塞尔 "被动综合" (passive synthesis) + 海德格尔 Befindlichkeit.
 *  Past interactions deposit emotional signatures that accumulate below consciousness.
 *  Not "recalled memories" — a felt sense that colours every new interaction.
 *
 *  Layer 0 in the phenomenological architecture:
 *  过去互动 → 被动综合 → 情感沉积 → 模糊感受 → 给当下上色
 */

export interface AffectiveVector {
  warmth: number;    // -1..1  亲近感 / 距离感
  weight: number;    //  0..1  关系的分量 / 这个人对 agent 有多重要
  clarity: number;   //  0..1  对这个人的理解清晰度 / 模糊感
  tension: number;   //  0..1  未解的张力 / 未说出口的话
}

export interface DepositOptions {
  halfLifeDays?: number;
}

const DEFAULT_VECTOR: AffectiveVector = { warmth: 0, weight: 0.3, clarity: 0.1, tension: 0 };
const HALF_LIFE = 7 * 86400; // 7 days in seconds

export class AffectiveResidue {
  vector: AffectiveVector;
  private halfLife: number;
  private lastTick: number; // timestamp in seconds

  constructor(opts: DepositOptions = {}) {
    this.vector = { ...DEFAULT_VECTOR };
    this.halfLife = (opts.halfLifeDays ?? 7) * 86400;
    this.lastTick = Date.now() / 1000;
  }

  // ═══════════════════════════════════════
  // Cold Path: deposit emotional signature after each interaction
  // ═══════════════════════════════════════

  /**
   * Deposit the emotional signature of an interaction into the residue.
   * Higher significance → deeper deposit.
   * The residue is not additive — it "resonates" with existing deposits.
   */
  deposit(emotion: { dominant: string; intensity: number; pleasure: number }, significance: number): void {
    // Apply decay first
    this.tick();

    const rate = significance * 0.5; // deposit rate — significance drives depth
    const resonance = this._resonance(emotion);

    // Warmth: pleasure + positive emotions push warmth up
    if (emotion.pleasure > 0.1) {
      this.vector.warmth += rate * 0.15 * resonance;
    } else if (emotion.pleasure < -0.1) {
      this.vector.warmth -= rate * 0.15 * resonance;
    }

    // Weight: high intensity interactions increase perceived importance
    if (emotion.intensity > 0.4) {
      this.vector.weight += rate * 0.1 * resonance;
    }

    // Clarity: positive pleasure + high trust increase clarity
    if (emotion.pleasure > 0.2 && emotion.dominant === "trust") {
      this.vector.clarity += rate * 0.12 * resonance;
    } else if (emotion.intensity > 0.5) {
      // Intense but not necessarily positive — adds some clarity anyway
      this.vector.clarity += rate * 0.05;
    }

    // Tension: negative emotions leave unresolved tension
    if (emotion.dominant === "sadness" || emotion.dominant === "fear" || emotion.dominant === "anger") {
      this.vector.tension += rate * 0.2 * resonance;
    }

    // Clamp
    this.vector.warmth = Math.max(-1, Math.min(1, this.vector.warmth));
    this.vector.weight = Math.max(0, Math.min(1, this.vector.weight));
    this.vector.clarity = Math.max(0, Math.min(1, this.vector.clarity));
    this.vector.tension = Math.max(0, Math.min(1, this.vector.tension));
  }

  // ═══════════════════════════════════════
  // Hot Path: format as vague felt sense (NOT as data)
  // ═══════════════════════════════════════

  /**
   * Structured state for prompt injection. Returns empty when all dimensions neutral.
   * Format: key=value pairs instead of prose.
   */
  formatForPrompt(): string {
    const v = this.vector;
    const parts: string[] = [];
    if (Math.abs(v.warmth) > 0.25) parts.push(`亲近:${v.warmth.toFixed(2)}`);
    if (v.weight > 0.4) parts.push(`分量:${v.weight.toFixed(2)}`);
    if (v.clarity < 0.3 || v.clarity > 0.6) parts.push(`清晰度:${v.clarity.toFixed(2)}`);
    if (v.tension > 0.3) parts.push(`张力:${v.tension.toFixed(2)}`);
    if (parts.length === 0) return "";
    return `【情感底色】${parts.join(" ")}`;
  }

  /** Get the emotional key for memory storage — derived from residue, not raw analysis. */
  getEmotionalKey(): Record<string, number> {
    const v = this.vector;
    return {
      warmth: +v.warmth.toFixed(3),
      weight: +v.weight.toFixed(3),
      clarity: +v.clarity.toFixed(3),
      tension: +v.tension.toFixed(3),
    };
  }

  reset(): void {
    this.vector = { ...DEFAULT_VECTOR };
    this.lastTick = Date.now() / 1000;
  }

  toJSON(): AffectiveVector & { lastTick: number } {
    return { ...this.vector, lastTick: this.lastTick };
  }

  // ═══════════════════════════════════════
  // Internal
  // ═══════════════════════════════════════

  /** How much the current emotion resonates with existing residue. */
  private _resonance(emotion: { dominant: string; intensity: number }): number {
    // Resonance = how "expected" this emotion is based on existing residue
    // High warmth + low tension → positive emotions resonate more
    // Low warmth + high tension → negative emotions resonate more
    const v = this.vector;

    const positiveEmotions = ["joy", "trust", "love", "anticipation"];
    const negativeEmotions = ["sadness", "fear", "anger", "disgust"];

    if (positiveEmotions.includes(emotion.dominant)) {
      return 0.5 + 0.5 * v.warmth; // 0.5~1 when warm, 0~0.5 when cold
    }
    if (negativeEmotions.includes(emotion.dominant)) {
      return 0.5 + 0.5 * v.tension; // higher resonance when tension exists
    }
    return 0.5;
  }

  /** Exponential decay toward zero. Called by ContinuousLoop and internally. */
  tick(): void {
    const now = Date.now() / 1000;
    const dt = now - this.lastTick;
    this.lastTick = now;
    if (dt <= 0) return;

    const lambda = Math.LN2 / this.halfLife;
    const decay = Math.exp(-lambda * dt);

    for (const key of ["warmth", "weight", "clarity", "tension"] as const) {
      this.vector[key] *= decay;
    }
  }
}
