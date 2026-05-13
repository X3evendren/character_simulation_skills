/**
 * MindState — Unified psychological state vector.
 * 
 *
 * Single source of truth for all psychological modules.
 * 7D state: pleasure, arousal, dominance, control, attachment, defense, goal_tension
 */
export class MindState {
  // PAD affect
  pleasure: number;    // -1.0 to 1.0
  arousal: number;     // 0.0 to 1.0
  dominance: number;   // -1.0 to 1.0

  // Control sense
  control: number;     // 0.0 to 1.0

  // Attachment
  attachmentActivation: number;  // 0.0 to 1.0
  attachmentStyle: string;

  // Schema activation
  schemaActivation: Record<string, number>;

  // Motivation / Goal
  goalTension: number;  // 0.0 to 1.0
  goalText: string;

  // Defense
  defenseStrength: number;  // 0.0 to 1.0
  defenseType: string;

  // Stability & time
  stability: number;     // 1.0 = stable, < 0.5 = drift warning
  timestamp: number;

  // OCEAN baseline (for stability anchoring)
  oceanBaseline: Record<string, number>;

  constructor(opts: Partial<MindState> = {}) {
    this.pleasure = opts.pleasure ?? 0.0;
    this.arousal = opts.arousal ?? 0.5;
    this.dominance = opts.dominance ?? 0.0;
    this.control = opts.control ?? 0.5;
    this.attachmentActivation = opts.attachmentActivation ?? 0.0;
    this.attachmentStyle = opts.attachmentStyle ?? 'secure';
    this.schemaActivation = opts.schemaActivation ?? {};
    this.goalTension = opts.goalTension ?? 0.5;
    this.goalText = opts.goalText ?? '';
    this.defenseStrength = opts.defenseStrength ?? 0.0;
    this.defenseType = opts.defenseType ?? '';
    this.stability = opts.stability ?? 1.0;
    this.timestamp = opts.timestamp ?? 0.0;
    this.oceanBaseline = opts.oceanBaseline ?? {
      O: 0.5, C: 0.5, E: 0.5, A: 0.5, N: 0.5,
    };
  }

  // ── Write interface ──

  setAffect(pleasure: number, arousal: number, dominance: number = 0.0): void {
    this.pleasure = clamp(pleasure, -1.0, 1.0);
    this.arousal = clamp(arousal, 0.0, 1.0);
    this.dominance = clamp(dominance, -1.0, 1.0);
    this.timestamp = Date.now() / 1000;
  }

  setAttachment(activation: number, style: string = ''): void {
    this.attachmentActivation = clamp(activation, 0.0, 1.0);
    if (style) this.attachmentStyle = style;
    this.timestamp = Date.now() / 1000;
  }

  setDefense(strength: number, dtype: string = ''): void {
    this.defenseStrength = clamp(strength, 0.0, 1.0);
    if (dtype) this.defenseType = dtype;
    this.timestamp = Date.now() / 1000;
  }

  activateSchema(name: string, intensity: number): void {
    this.schemaActivation[name] = clamp(intensity, 0.0, 1.0);
    this.timestamp = Date.now() / 1000;
  }

  setGoal(tension: number, text: string = ''): void {
    this.goalTension = clamp(tension, 0.0, 1.0);
    if (text) this.goalText = text;
    this.timestamp = Date.now() / 1000;
  }

  setControl(value: number): void {
    this.control = clamp(value, 0.0, 1.0);
    this.timestamp = Date.now() / 1000;
  }

  // ── Coherence ──

  computeCoherence(): number {
    let coherence = 1.0;
    if (this.pleasure > 0.3 && this.defenseStrength > 0.6) coherence -= 0.2;
    if (this.arousal > 0.7 && this.control > 0.7) coherence -= 0.1;
    if (this.attachmentActivation > 0.7 && this.defenseStrength > 0.7) coherence -= 0.3;
    if (this.pleasure < -0.5 && this.arousal < 0.2) coherence -= 0.1;
    return Math.max(0.0, coherence);
  }

  distanceTo(other: MindState): number {
    // Normalized distance in 7D state space
    const d = Math.sqrt(
      ((this.pleasure - other.pleasure) / 2) ** 2 +
      (this.arousal - other.arousal) ** 2 +
      ((this.dominance - other.dominance) / 2) ** 2 +
      (this.control - other.control) ** 2 +
      (this.attachmentActivation - other.attachmentActivation) ** 2 +
      (this.defenseStrength - other.defenseStrength) ** 2 +
      (this.goalTension - other.goalTension) ** 2
    );
    return d / Math.sqrt(7);
  }

  checkStability(): { stable: boolean; index: number; issues: string[] } {
    const issues: string[] = [];
    this.stability = 1.0;
    if (this.defenseStrength > 0.8) {
      issues.push('防御机制过度激活');
      this.stability -= 0.1;
    }
    if (this.attachmentActivation > 0.9 && this.attachmentStyle === 'avoidant') {
      issues.push('回避型依恋高度激活——内在矛盾');
      this.stability -= 0.15;
    }
    if (this.pleasure < -0.6) {
      issues.push('情感状态持续负面');
      this.stability -= 0.1;
    }
    return { stable: this.stability >= 0.5, index: this.stability, issues };
  }

  // ── Serialization ──

  clone(): MindState {
    return new MindState({
      pleasure: this.pleasure,
      arousal: this.arousal,
      dominance: this.dominance,
      control: this.control,
      attachmentActivation: this.attachmentActivation,
      attachmentStyle: this.attachmentStyle,
      schemaActivation: { ...this.schemaActivation },
      goalTension: this.goalTension,
      goalText: this.goalText,
      defenseStrength: this.defenseStrength,
      defenseType: this.defenseType,
      stability: this.stability,
      timestamp: Date.now() / 1000,
      oceanBaseline: { ...this.oceanBaseline },
    });
  }

  toDict(): Record<string, unknown> {
    return {
      affect: { pleasure: this.pleasure, arousal: this.arousal, dominance: this.dominance },
      control: this.control,
      attachment: { activation: this.attachmentActivation, style: this.attachmentStyle },
      schemas: { ...this.schemaActivation },
      goal: { tension: this.goalTension, text: this.goalText },
      defense: { strength: this.defenseStrength, type: this.defenseType },
      stability: this.stability,
      coherence: this.computeCoherence(),
      timestamp: this.timestamp,
    };
  }

  static fromDict(d: Record<string, any>): MindState {
    const affect = d.affect ?? {};
    const attachment = d.attachment ?? {};
    const goal = d.goal ?? {};
    const defense = d.defense ?? {};
    return new MindState({
      pleasure: affect.pleasure ?? 0.0,
      arousal: affect.arousal ?? 0.5,
      dominance: affect.dominance ?? 0.0,
      control: d.control ?? 0.5,
      attachmentActivation: attachment.activation ?? 0.0,
      attachmentStyle: attachment.style ?? 'secure',
      schemaActivation: d.schemas ?? {},
      goalTension: goal.tension ?? 0.5,
      goalText: goal.text ?? '',
      defenseStrength: defense.strength ?? 0.0,
      defenseType: defense.type ?? '',
      stability: d.stability ?? 1.0,
      timestamp: d.timestamp ?? 0.0,
    });
  }
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}
