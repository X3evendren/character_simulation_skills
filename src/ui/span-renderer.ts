/** Span State — reactive span container for Ink rendering.
 *  Manages span lifecycle: FLUID → STABLE → LOCKED.
 *  Not a React component — pure state with subscriber pattern.
 */
import type { Span, SpanOp, SpanLayer } from "../generation/types";

export interface SpanStateSnapshot {
  lockedSpans: Span[];
  stableSpans: Span[];
  fluidSpans: Span[];
  frozen: boolean;
}

type Listener = () => void;

export class SpanState {
  private lockedSpans: Span[] = [];
  private stableSpans: Span[] = [];
  private fluidSpans: Span[] = [];
  frozen = false;
  private listeners = new Set<Listener>();

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private notify(): void {
    for (const fn of this.listeners) fn();
  }

  apply(op: SpanOp): void {
    switch (op.type) {
      case "append": {
        op.span.layer = "fluid";
        this.fluidSpans.push(op.span);
        break;
      }
      case "patch": {
        // Find span in stable or locked
        const target = this.stableSpans.find(s => s.id === op.spanId)
          ?? this.lockedSpans.find(s => s.id === op.spanId);
        if (target) {
          const lenDiff = op.newText.length - target.text.length;
          target.text = op.newText;
          target.endPos = target.startPos + op.newText.length;
          // Shift subsequent spans
          this._shiftPositions(target.endPos, lenDiff);
        }
        break;
      }
      case "lock": {
        // Find span and promote to next layer
        const fluidIdx = this.fluidSpans.findIndex(s => s.id === op.spanId);
        if (fluidIdx >= 0) {
          const span = this.fluidSpans[fluidIdx];
          this.fluidSpans.splice(fluidIdx, 1);
          span.layer = "stable";
          span.committedAt = Date.now();
          this.stableSpans.push(span);
        } else {
          const stableIdx = this.stableSpans.findIndex(s => s.id === op.spanId);
          if (stableIdx >= 0) {
            const span = this.stableSpans[stableIdx];
            this.stableSpans.splice(stableIdx, 1);
            span.layer = "locked";
            span.committedAt = Date.now();
            this.lockedSpans.push(span);
          }
        }
        break;
      }
      case "invalidate": {
        // Clear FLUID spans from the given spanId onward
        const idx = this.fluidSpans.findIndex(s => s.id === op.fromSpanId);
        if (idx >= 0) {
          this.fluidSpans = this.fluidSpans.slice(0, idx);
        }
        break;
      }
    }
    this.notify();
  }

  freeze(): void {
    this.fluidSpans = [];
    this.frozen = true;
    this.notify();
  }

  /** Get ordered spans for rendering (locked → stable → fluid). */
  getAllSpans(): Span[] {
    return [...this.lockedSpans, ...this.stableSpans, ...this.fluidSpans];
  }

  getFluidSpans(): Span[] { return [...this.fluidSpans]; }
  getStableSpans(): Span[] { return [...this.stableSpans]; }
  getLockedSpans(): Span[] { return [...this.lockedSpans]; }

  snapshot(): SpanStateSnapshot {
    return {
      lockedSpans: [...this.lockedSpans],
      stableSpans: [...this.stableSpans],
      fluidSpans: [...this.fluidSpans],
      frozen: this.frozen,
    };
  }

  reset(): void {
    this.lockedSpans = [];
    this.stableSpans = [];
    this.fluidSpans = [];
    this.frozen = false;
    this.notify();
  }

  private _shiftPositions(afterPos: number, delta: number): void {
    for (const spans of [this.stableSpans, this.lockedSpans]) {
      for (const s of spans) {
        if (s.startPos >= afterPos) {
          s.startPos += delta;
          s.endPos += delta;
        } else if (s.endPos > afterPos) {
          s.endPos += delta;
        }
      }
    }
  }
}
