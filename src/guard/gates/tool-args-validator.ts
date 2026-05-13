/**
 * Gate 1b: Tool Arguments Validator — cross-tool parameter constraints.
 * Complements the per-tool Zod schema validation with cross-cutting rules.
 */
import type { GuardGate, GateResult, ToolCallInfo } from "../pipeline";

/** Paths that write tools should never touch */
const PROTECTED_PATHS = [
  /node_modules/,
  /\.git\b/,
  /\.env$/,
  /\.claude\b/,
  /\/proc\//,
  /C:\\Windows/i,
];

/** Dangerous command patterns — stricter than permission audit */
const DANGEROUS_COMMANDS: RegExp[] = [
  /rm\s+(-rf?\s+|--recursive)/,
  /del\s+\/f/i,
  /format\s+/i,
  /mkfs\./,
  />\s*\/dev\//,
];

export function createToolArgsValidatorGate(): GuardGate {
  return {
    name: "tool-args-validator",

    onToolCall(tool: ToolCallInfo): GateResult {
      const { name, arguments: args } = tool;
      const path = (args.path as string) ?? "";

      // Check write operations against protected paths
      if (name === "write_file" || name === "edit_file") {
        if (path) {
          for (const pat of PROTECTED_PATHS) {
            if (pat.test(path)) {
              return {
                passed: false,
                action: "block",
                reason: `Cannot write to protected path: ${path}`,
              };
            }
          }
        }
        // write_file requires content
        if (name === "write_file" && !(args.content as string)?.trim()) {
          return {
            passed: false,
            action: "block",
            reason: "write_file called with empty content",
          };
        }
      }

      // exec_command safety: block explicitly dangerous commands
      if (name === "exec_command") {
        const cmd = (args.command as string) ?? "";
        for (const pat of DANGEROUS_COMMANDS) {
          if (pat.test(cmd)) {
            return {
              passed: false,
              action: "block",
              reason: `Dangerous command blocked: ${cmd.slice(0, 100)}`,
            };
          }
        }
        // Prevent commands targeting protected paths
        for (const pp of PROTECTED_PATHS) {
          if (pp.test(cmd)) {
            return {
              passed: false,
              action: "block",
              reason: `Command targets protected path: ${cmd.slice(0, 100)}`,
            };
          }
        }
      }

      // web_fetch: validate URL format
      if (name === "web_fetch") {
        const url = (args.url as string) ?? "";
        if (url && !/^https?:\/\/.+/.test(url)) {
          return {
            passed: false,
            action: "block",
            reason: `Invalid URL: ${url.slice(0, 100)}`,
          };
        }
      }

      return { passed: true, action: "allow" };
    },
  };
}
