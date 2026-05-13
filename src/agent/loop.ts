/**
 * ContinuousLoop — Background tick that keeps agent state alive between inputs.
 *
 * Principles:
 *   - All tick operations are deterministic computations (no LLM calls)
 *   - Two drives: "reduce future uncertainty" + "maintain internal stability"
 *   - LLM only intervenes when user speaks or initiative threshold is crossed
 */
import type { CharacterAgent } from "./agent";

export class ContinuousLoop {
  private interval: number;
  private timer: ReturnType<typeof setInterval> | null = null;
  private lastTick = 0;
  tickCount = 0;

  constructor(intervalMs = 30_000) {
    this.interval = intervalMs;
  }

  start(agent: CharacterAgent): void {
    if (this.timer) return;
    this.lastTick = Date.now();
    this.timer = setInterval(() => this._tick(agent), this.interval);
  }

  stop(): void {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
  }

  get running(): boolean { return this.timer !== null; }

  private _tick(agent: CharacterAgent): void {
    const now = Date.now();
    const dt = (now - this.lastTick) / 1000; // seconds
    this.lastTick = now;
    this.tickCount++;

    try {
      // ═══════════════════════════════════════
      // 1. Maintain internal stability
      // ═══════════════════════════════════════
      agent.saturation.tick(dt);          // saturation natural decay
      agent.affectiveResidue.tick();      // emotional decay
      agent.drives.tick(dt);              // drive values return to baseline

      // ═══════════════════════════════════════
      // 2. Reduce future uncertainty
      // ═══════════════════════════════════════
      agent.selfModel.consolidate();      // learn from interaction patterns

      // ═══════════════════════════════════════
      // 3. Initiative check (future: auto-trigger conversation)
      // ═══════════════════════════════════════
      // Reserved for when temporal horizon protention tension implementation is ready.
      // if (agent.temporalHorizon.shouldInitiate()) { ... }
    } catch {
      // Tick failures must not crash the agent
    }
  }
}
