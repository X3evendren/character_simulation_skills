/** Drive Sublimator — convert drive values to natural-language biases.
 *
 *  Phenomenology: 弗洛伊德升华 (Trieb→expression) + 梅洛-庞蒂 "我能先于我想".
 *  Drives are NEVER injected as parameter values into the prompt.
 *  They only affect behavior through two indirect channels:
 *
 *  Channel A: Attention bias — a felt sense of where attention is drawn
 *  Channel B: Style modulation — micro-adjustments to sampling parameters
 *
 *  Only the dominant 1-2 drives express. Others stay silent.
 */

import type { DriveState, DesireData } from "./desires";

export interface StyleHints {
  temperatureShift: number;
  maxTokensShift: number;
}

export interface DriveBiasResult {
  attentionText: string;        // for prompt injection (empty if neutral)
  styleHints: StyleHints;       // for sampling micro-adjustments
  dominantNames: string[];      // which drives are expressing
}

// ═══════════════════════════════════════
// Natural language mappings
// ═══════════════════════════════════════

/** Convert a single drive into a first-person felt sense. */
function driveToFeltSense(d: DesireData): string {
  const ratio = d.intensity / d.threshold; // >1 = urgent, <1 = satisfied

  const high: Record<string, string[]> = {
    curiosity: [
      "你发现自己对这个话题有很深的兴趣，不自觉地想挖得更深",
      "你感到一种求知的冲动——想知道更多",
      "有什么在吸引你继续追问下去",
    ],
    helpfulness: [
      "你本能地想为对方做点什么",
      "你感到一种想帮忙的冲动",
      "你察觉到自己想提供有用的信息",
    ],
    achievement: [
      "你有一种想把事情彻底搞清楚的劲头",
      "你感到解决这个问题的驱动力",
      "你发现自己想做得更精确、更完整",
    ],
    connection: [
      "你想靠得更近一点，了解对方更多",
      "你感到一种温暖的、想连接的方向",
      "你发现自己想和对方建立更深的联系",
    ],
    autonomy: [
      "你感到自己今天很独立，不太需要别人的认可",
      "你有自己的想法，不太想被带着走",
      "你发现自己想保持自己的节奏",
    ],
  };

  const low: Record<string, string[]> = {
    curiosity: [
      "你似乎不太想深究这个话题",
    ],
    helpfulness: [
      "你觉得自己今天不太有帮忙的兴致",
    ],
    achievement: [
      "你觉得差不多就行了",
    ],
    connection: [
      "你感到一种微妙的距离感",
    ],
    autonomy: [
      "你发现自己今天有点依赖对方的引导",
    ],
  };

  const pool = ratio > 0.85 ? high[d.name] : ratio < 0.5 ? low[d.name] : null;
  if (!pool) return "";

  // Deterministic selection based on intensity so it's stable within a turn
  const idx = Math.floor(d.intensity * 10) % pool.length;
  return pool[idx] ?? "";
}

// ═══════════════════════════════════════
// Style hints
// ═══════════════════════════════════════

function driveToStyleHints(dominant: DesireData[]): StyleHints {
  const hints: StyleHints = { temperatureShift: 0, maxTokensShift: 0 };

  for (const d of dominant) {
    const ratio = d.intensity / d.threshold;

    switch (d.name) {
      case "connection":
        // Warmer, slightly longer
        hints.temperatureShift += 0.03 * ratio;
        hints.maxTokensShift += 30 * ratio;
        break;
      case "autonomy":
        // Cooler, shorter
        hints.temperatureShift -= 0.03 * ratio;
        hints.maxTokensShift -= 20 * ratio;
        break;
      case "achievement":
        // More precise → lower temperature
        hints.temperatureShift -= 0.02 * ratio;
        hints.maxTokensShift += 20 * ratio;
        break;
      case "curiosity":
        // More exploratory → higher temperature
        hints.temperatureShift += 0.02 * ratio;
        hints.maxTokensShift += 20 * ratio;
        break;
      case "helpfulness":
        hints.maxTokensShift += 20 * ratio;
        break;
    }
  }

  // Clamp
  hints.temperatureShift = Math.max(-0.15, Math.min(0.15, hints.temperatureShift));
  hints.maxTokensShift = Math.max(-100, Math.min(100, hints.maxTokensShift));

  return hints;
}

// ═══════════════════════════════════════
// Main class
// ═══════════════════════════════════════

export class DriveSublimator {
  /** Select the top N drives that are significantly deviated from baseline. */
  selectDominantDrives(drives: DriveState, topN = 2): DesireData[] {
    const all = Object.values(drives.desires);
    // Only drives that are either urgent (above threshold) or very satisfied (below 0.4)
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

  /** Channel A: Build attention bias text for prompt injection.
   *  Only fires when drives are significantly deviated from baseline. */
  buildAttentionBias(drives: DriveState): string {
    const dominant = this.selectDominantDrives(drives);
    const parts: string[] = [];

    for (const d of dominant) {
      const felt = driveToFeltSense(d);
      if (felt) parts.push(felt);
    }

    if (parts.length === 0) return "";

    // At most 2 parts, joined naturally
    const chosen = parts.slice(0, 2);
    return `【你此刻的内在倾向 — 不是命令，只是你发现自己正在感受的方向】\n${chosen.join("。\n")}。`;
  }

  /** Channel B: Build style hints for sampling micro-adjustments. */
  buildStyleHints(drives: DriveState): StyleHints {
    const dominant = this.selectDominantDrives(drives, 2);
    return driveToStyleHints(dominant);
  }

  /** Combined result for Hot Path injection. */
  build(drives: DriveState): DriveBiasResult {
    const dominant = this.selectDominantDrives(drives);
    return {
      attentionText: this.buildAttentionBias(drives),
      styleHints: this.buildStyleHints(drives),
      dominantNames: dominant.map(d => d.name),
    };
  }
}
