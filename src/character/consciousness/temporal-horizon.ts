/** Temporal Horizon — inner time-consciousness structure.
 *
 *  Phenomenology: 胡塞尔内时间意识三相位 (retention-impression-protention).
 *  The present is not a point but a field — what just was, what is, what is about to be.
 *
 *  Retention: the just-past still held in the present. Like a note still resonating.
 *  Protention: the already-expected next. Like reading a sentence and knowing it's not over.
 *
 *  In agent terms:
 *  - Retention = last turn's emotional residue, still echoing (but fading)
 *  - Protention = expectation that user will respond; tension builds in silence
 *  - Tick = autonomous drift when no external input arrives
 */

export interface RetentionState {
  emotionDominant: string;   // 上轮的主导情绪
  emotionIntensity: number;  // 残留强度 (指数衰减)
  unfinished: boolean;       // 上轮是否感觉没说完整
  sinceLastTurn: number;     // 距上轮多少秒
}

export interface ProtentionState {
  expectingResponse: boolean;
  expectedTopic: string;
  tension: number;           // 0..1, 等待越久张力越高
}

const RETENTION_HALF_LIFE = 30; // seconds — emotion echoes fade fast
const TENSION_BUILD_RATE = 0.02; // per second of silence
const TENSION_DECAY_RATE = 0.5;  // per turn (user responds → tension drops)
const TENSION_THRESHOLD = 0.7;   // above this → agent may take initiative (future)

export class TemporalHorizon {
  retention: RetentionState;
  protention: ProtentionState;
  private lastTurnEnd: number; // timestamp

  constructor() {
    this.retention = {
      emotionDominant: "neutral",
      emotionIntensity: 0,
      unfinished: false,
      sinceLastTurn: 0,
    };
    this.protention = {
      expectingResponse: true,
      expectedTopic: "",
      tension: 0,
    };
    this.lastTurnEnd = Date.now() / 1000;
  }

  // ═══════════════════════════════════════
  // Turn lifecycle — called by Cold Path
  // ═══════════════════════════════════════

  /** Called at the start of a new turn — retention from previous turn enters awareness. */
  onTurnStart(): void {
    const now = Date.now() / 1000;
    const dt = now - this.lastTurnEnd;
    this.retention.sinceLastTurn = dt;

    // Decay retention
    const lambda = Math.LN2 / RETENTION_HALF_LIFE;
    this.retention.emotionIntensity *= Math.exp(-lambda * dt);

    if (this.retention.emotionIntensity < 0.05) {
      this.retention.emotionDominant = "neutral";
      this.retention.emotionIntensity = 0;
      this.retention.unfinished = false;
    }

    // User responded → tension partially resolved
    this.protention.tension = Math.max(0, this.protention.tension - TENSION_DECAY_RATE);
    this.protention.expectingResponse = false;
  }

  /** Called after generation completes — sets up retention for the NEXT turn. */
  onTurnEnd(emotion: { dominant: string; intensity: number }, unfinished: boolean): void {
    this.lastTurnEnd = Date.now() / 1000;
    this.retention.emotionDominant = emotion.dominant;
    this.retention.emotionIntensity = emotion.intensity;
    this.retention.unfinished = unfinished;
    this.retention.sinceLastTurn = 0;

    // Set up protention — agent now expects user to respond
    this.protention.expectingResponse = true;
  }

  // ═══════════════════════════════════════
  // Autonomous tick — called periodically or at turn start
  // ═══════════════════════════════════════

  /** Advance time — decay retention, build protention tension. */
  tick(dtSeconds: number): void {
    // Decay retention
    const lambda = Math.LN2 / RETENTION_HALF_LIFE;
    this.retention.emotionIntensity *= Math.exp(-lambda * dtSeconds);
    this.retention.sinceLastTurn += dtSeconds;

    if (this.retention.emotionIntensity < 0.05) {
      this.retention.emotionDominant = "neutral";
      this.retention.emotionIntensity = 0;
    }

    // Build protention tension when expecting response but none arrives
    if (this.protention.expectingResponse) {
      this.protention.tension = Math.min(1, this.protention.tension + TENSION_BUILD_RATE * dtSeconds);
    }
  }

  /** Whether protention tension is high enough for autonomous initiative (future feature). */
  shouldTakeInitiative(): boolean {
    return this.protention.tension > TENSION_THRESHOLD;
  }

  // ═══════════════════════════════════════
  // Hot Path: format as subtle temporal awareness
  // ═══════════════════════════════════════

  /**
   * Only injects when retention is significantly non-neutral.
   * Most turns this returns empty — the temporal horizon is usually silent.
   */
  formatForPrompt(): string {
    const r = this.retention;
    const p = this.protention;

    // Nothing to say — retention has fully decayed
    if (r.emotionIntensity < 0.15 && !r.unfinished) return "";

    const parts: string[] = [];

    // Strong lingering emotion
    if (r.emotionIntensity > 0.4 && r.emotionDominant !== "neutral") {
      const map: Record<string, string> = {
        joy: "刚才的愉快还在心里回荡",
        sadness: "刚才的难过还没完全消散",
        fear: "刚才的不安还在",
        anger: "刚才有些不快，还在平复",
        trust: "刚才感到的信任还在",
        anticipation: "还在期待着什么",
        surprise: "刚才的意外还在消化",
        disgust: "本能地还想回避",
      };
      const desc = map[r.emotionDominant];
      if (desc) parts.push(desc);
      else parts.push("刚才的感受还在心里"); // fallback for unmapped labels (e.g. "低落", "温暖")
    } else if (r.emotionIntensity > 0.15) {
      parts.push("刚才的感觉还留有余韵");
    }

    // Unfinished feeling
    if (r.unfinished) {
      parts.push("你感到自己还有话没说完");
    }

    // Silence tension (for future: could trigger initiative)
    if (p.tension > 0.5 && p.tension <= TENSION_THRESHOLD) {
      parts.push("你注意到已经安静了一会儿");
    }

    if (parts.length === 0) return "";

    const chosen = parts.slice(0, 2);
    return `【时间感受 — 不是记忆，而是刚才还在回荡的感受】\n${chosen.join("。\n")}。`;
  }

  // ═══════════════════════════════════════
  // Future: autonomous initiative prompt
  // ═══════════════════════════════════════

  /** When protention tension is high, generate a reason the agent might speak. */
  getInitiativeContext(): string {
    if (!this.shouldTakeInitiative()) return "";

    const lines = ["你注意到已经安静了一会儿。"];
    if (this.retention.unfinished) {
      lines.push("你感觉自己刚才还没说完。");
    }
    if (this.retention.emotionIntensity > 0.2) {
      lines.push("刚才的感受还在，你觉得可以继续这个话题。");
    }
    return lines.join(" ");
  }

  reset(): void {
    this.retention = { emotionDominant: "neutral", emotionIntensity: 0, unfinished: false, sinceLastTurn: 0 };
    this.protention = { expectingResponse: true, expectedTopic: "", tension: 0 };
    this.lastTurnEnd = Date.now() / 1000;
  }

  toJSON(): unknown {
    return {
      retention: { ...this.retention },
      protention: { ...this.protention },
      lastTurnEnd: this.lastTurnEnd,
    };
  }
}
