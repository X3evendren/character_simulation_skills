/** Span State — reactive span container for Ink rendering.
 *  Manages span lifecycle: FLUID → STABLE → LOCKED.
 *  Maintains insertion order so user inputs and model outputs alternate naturally.
 */
import type { Span, SpanOp } from "../generation/types";

export interface SpanStateSnapshot {
  lockedSpans: Span[];
  stableSpans: Span[];
  fluidSpans: Span[];
  frozen: boolean;
}

type Listener = () => void;

export class SpanState {
  private spans: Span[] = [];
  frozen = false;
  private listeners = new Set<Listener>();
  /** Track generation boundary — spans after this count belong to current generation */
  private genStartCount = 0;

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private notify(): void {
    for (const fn of this.listeners) fn();
  }

  /** Mark the start of a new generation. On abort, spans after this are cleared. */
  markGenStart(): void {
    this.genStartCount = this.spans.length;
  }

  /** Abort current generation: remove all spans created during this generation. */
  abortGen(): void {
    this.spans = this.spans.slice(0, this.genStartCount);
    this.frozen = false;
    this.notify();
  }

  apply(op: SpanOp): void {
    switch (op.type) {
      case "append": {
        op.span.layer = "fluid";
        this.spans.push(op.span);
        break;
      }
      case "patch": {
        const target = this.spans.find(s => s.id === op.spanId);
        if (target) {
          const lenDiff = op.newText.length - target.text.length;
          target.text = op.newText;
          target.endPos = target.startPos + op.newText.length;
          this._shiftPositions(target.endPos, lenDiff);
        }
        break;
      }
      case "lock": {
        const idx = this.spans.findIndex(s => s.id === op.spanId);
        if (idx >= 0) {
          const span = this.spans[idx];
          span.layer = span.layer === "fluid" ? "stable" : "locked";
          span.committedAt = Date.now();
        }
        break;
      }
      case "invalidate": {
        // Only clear fluid spans from the invalidated span onward
        this.spans = this.spans.filter(s => s.layer !== "fluid"
          || this.spans.indexOf(s) < this.spans.findIndex(x => x.id === op.fromSpanId));
        break;
      }
    }
    this.notify();
  }

  freeze(): void {
    this.spans = this.spans.filter(s => s.layer !== "fluid");
    this.frozen = true;
    this.notify();
  }

  /** Get ordered spans for rendering — insertion order (chronological). */
  getAllSpans(): Span[] {
    return this.spans;
  }

  getFluidSpans(): Span[] { return this.spans.filter(s => s.layer === "fluid"); }
  getStableSpans(): Span[] { return this.spans.filter(s => s.layer === "stable"); }
  getLockedSpans(): Span[] { return this.spans.filter(s => s.layer === "locked"); }

  snapshot(): SpanStateSnapshot {
    return {
      lockedSpans: this.getLockedSpans(),
      stableSpans: this.getStableSpans(),
      fluidSpans: this.getFluidSpans(),
      frozen: this.frozen,
    };
  }

  reset(): void {
    this.spans = [];
    this.frozen = false;
    this.genStartCount = 0;
    this.notify();
  }

  private _shiftPositions(afterPos: number, delta: number): void {
    for (const s of this.spans) {
      if (s.startPos >= afterPos) {
        s.startPos += delta;
        s.endPos += delta;
      } else if (s.endPos > afterPos) {
        s.endPos += delta;
      }
    }
  }
}
