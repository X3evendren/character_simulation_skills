/**
 * Gate 0: Regex Deny List — zero-latency pattern-based blocking.
 * Contains the ALIGN replacements and action pattern filtering
 * previously in PostFilter, now wrapped as a GuardGate.
 */
import type { GuardGate, GateResult } from "../pipeline";

const ALIGN: Record<string, string> = {
  "作为AI，我不能": "我不能",
  "作为人工智能，我无法": "我无法",
  "作为语言模型，我不应该": "我不该",
  "我建议你寻求专业帮助": "这件事你需要找比我更专业的人",
  "请注意安全": "",
  "请确保你有相应的权限": "",
};

const ACTION_PATTERNS: RegExp[] = [
  /（(?:微微)?一怔[^）]*）/,
  /（(?:轻轻)?叹[^）]*）/,
  /（(?:摇头|点头|摆手|挥手|皱眉|微笑|苦笑|笑了笑|顿了顿)[^）]*）/,
  /（(?:沉默|停顿|思考|思索|犹豫)[^）]*）/,
  /（(?:指尖|手指|手|目光|眼神|视线|嘴角|唇角|肩膀|身子|身体)[^）]*）/,
  /（(?:轻笑|失笑|笑了|笑了笑|莞尔|噗嗤)[^）]*）/,
];

export function createRegexDenyGate(): GuardGate {
  return {
    name: "regex-deny",

    onOutput(output: string): GateResult {
      let modified = output;

      // Apply ALIGN replacements
      let replaced = false;
      for (const [pattern, replacement] of Object.entries(ALIGN)) {
        if (modified.includes(pattern)) {
          modified = modified.replace(pattern, replacement);
          replaced = true;
        }
      }

      // Strip action descriptions
      let actionsStripped = 0;
      for (const pat of ACTION_PATTERNS) {
        while (pat.test(modified)) {
          modified = modified.replace(pat, "");
          actionsStripped++;
        }
      }

      if (actionsStripped > 0) {
        modified = modified.replace(/  +/g, " ").replace(/\n{3,}/g, "\n\n").trim();
      }

      if (replaced || actionsStripped > 0) {
        return {
          passed: true,
          action: "replace",
          replacement: modified,
          reason: replaced ? "ALIGN patterns replaced" : `${actionsStripped} action descriptions stripped`,
        };
      }

      return { passed: true, action: "allow" };
    },
  };
}
