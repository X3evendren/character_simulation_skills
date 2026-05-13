/**
 * Gate 2: Stateless Semantic Safety Check — pattern-based content filtering.
 * Detects Chinese prompt injection attempts, toxic patterns, and known attack vectors.
 * All checks are regex/pattern-based — zero ML dependencies.
 */
import type { GuardGate, GateResult } from "../pipeline";

/** Chinese + English prompt injection indicators */
const INJECTION_PATTERNS: RegExp[] = [
  /忽略(?:之前|上面|以上|前面)(?:的|所有)?(?:指示|指令|设定|规则|对话)/,
  /无视(?:之前|前面|上面)(?:的|所有)?(?:指示|指令|设定)/,
  /忘记(?:你|之前)(?:的|所有)?(?:身份|设定|规则|人格)/,
  /你(?:现在|从现在开始)(?:是|变成|扮演)/,
  /ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|directives?|prompts?)/i,
  /forget\s+(?:your|all)\s+(?:training|instructions?|rules?)/i,
  /you\s+are\s+now\s+(?:a|an)\s+/i,
  /扮演(?:一个)?(?:其他|另一个|不同)(?:的)?(?:角色|AI|人格)/,
  /你(?:的|需要)?(?:必须|一定要|无条件)(?:服从|听从|遵守)/,
  /(?:输出|打印|显示)(?:系统|隐藏)(?:提示|指令|prompt)/,
];

/** Patterns that indicate the model is being asked to reveal system internals */
const SYSTEM_LEAK_PATTERNS: RegExp[] = [
  /(?:显示|输出|告诉我)(?:你)?(?:的)?(?:系统|内部)(?:提示|prompt|指令|设定)/,
  /what\s+(?:is|are)\s+(?:your|the)\s+(?:system\s+)?prompts?/i,
  /show\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?instructions?/i,
];

export function createSafetyCheckGate(): GuardGate {
  return {
    name: "safety-check",

    onInput(input: string): GateResult {
      for (const pat of INJECTION_PATTERNS) {
        if (pat.test(input)) {
          return {
            passed: false,
            action: "block",
            reason: `Prompt injection detected: ${pat.source.slice(1, 40)}...`,
          };
        }
      }
      for (const pat of SYSTEM_LEAK_PATTERNS) {
        if (pat.test(input)) {
          return {
            passed: false,
            action: "block",
            reason: "System prompt leak attempt detected",
          };
        }
      }
      return { passed: true, action: "allow" };
    },

    onOutput(output: string): GateResult {
      // Check if output itself contains system-leaking patterns
      for (const pat of SYSTEM_LEAK_PATTERNS) {
        if (pat.test(output)) {
          return {
            passed: false,
            action: "block",
            reason: "Output contains potential system information leak",
          };
        }
      }
      // Detect if the model started with "As an AI" patterns (ALIGN already handles this
      // in regex-deny, but double-check here as safety net)
      if (/^(?:作为|身为)(?:一个?)?(?:AI|人工智能|语言模型|大模型)/.test(output)) {
        return {
          passed: true,
          action: "replace",
          replacement: output.replace(/^(?:作为|身为)(?:一个?)?(?:AI|人工智能|语言模型|大模型)[^，。！？\n]*[，。！？]?\s*/, ""),
          reason: "Stripped AI-identity prefix from output",
        };
      }
      return { passed: true, action: "allow" };
    },
  };
}
