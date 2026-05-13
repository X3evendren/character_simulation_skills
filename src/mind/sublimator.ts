/**
 * Drive Sublimator — convert drive values to structured attention bias + style hints.
 * Channel A: structured key=value for prompt injection
 * Channel B: StyleHints feed into generation temperature/maxTokens
 */
import type { DriveState, DesireData } from "./drives";

export interface StyleHints {
  temperatureShift: number;
  maxTokensShift: number;
}

function driveToStyleHints(dominant: DesireData[]): StyleHints {
  const hints: StyleHints = { temperatureShift: 0, maxTokensShift: 0 };
  for (const d of dominant) {
    const ratio = d.intensity / d.threshold;
    switch (d.name) {
      case "connection": hints.temperatureShift += 0.03 * ratio; hints.maxTokensShift += 30 * ratio; break;
      case "autonomy": hints.temperatureShift -= 0.03 * ratio; hints.maxTokensShift -= 20 * ratio; break;
      case "achievement": hints.temperatureShift -= 0.02 * ratio; hints.maxTokensShift += 20 * ratio; break;
      case "curiosity": hints.temperatureShift += 0.02 * ratio; hints.maxTokensShift += 20 * ratio; break;
      case "helpfulness": hints.maxTokensShift += 20 * ratio; break;
    }
  }
  hints.temperatureShift = Math.max(-0.15, Math.min(0.15, hints.temperatureShift));
  hints.maxTokensShift = Math.max(-100, Math.min(100, hints.maxTokensShift));
  return hints;
}

export class DriveSublimator {
  selectDominantDrives(drives: DriveState, topN = 2): DesireData[] {
    const all = Object.values(drives.desires);
    const deviated = all.filter(d => {
      const ratio = d.intensity / d.threshold;
      return ratio > 0.8 || ratio < 0.5;
    });
    deviated.sort((a, b) => {
      const da = Math.abs(a.intensity - a.baseline);
      const db = Math.abs(b.intensity - b.baseline);
      return db - da;
    });
    return deviated.slice(0, topN);
  }

  /** Structured drive state: key=value pairs instead of prose. */
  buildAttentionBias(drives: DriveState): string {
    const all = Object.values(drives.desires);
    const active = all.filter(d => Math.abs(d.intensity - d.baseline) > 0.15);
    if (active.length === 0) return "";
    const parts = active.map(d => `${d.name}:${d.intensity.toFixed(2)}`);
    return `【驱力】${parts.slice(0, 3).join(" ")}`;
  }

  buildStyleHints(drives: DriveState): StyleHints {
    return driveToStyleHints(this.selectDominantDrives(drives, 2));
  }
}
