/**
 * Gate 3: Tool Result Validator — post-execution result sanity checks.
 * Flags suspicious tool results that might indicate hallucinated execution.
 */
import type { GuardGate, GateResult, ToolResultInfo } from "../pipeline";

export function createToolResultValidatorGate(): GuardGate {
  return {
    name: "tool-result-validator",

    onToolResult(result: ToolResultInfo): GateResult {
      const { name, success, output, error } = result;

      // read_file: should have content
      if (name === "read_file") {
        if (success && (!output || output.length < 2)) {
          return {
            passed: false,
            action: "block",
            reason: `read_file reported success but output is empty — possible hallucination`,
          };
        }
        if (output && output.startsWith("Error reading")) {
          return {
            passed: false,
            action: "block",
            reason: `read_file output looks like an error message`,
          };
        }
      }

      // exec_command: check for common error patterns in output
      if (name === "exec_command") {
        if (success && output) {
          const lower = output.toLowerCase();
          const errorIndicators = [
            "command not found", "不是内部或外部命令", "is not recognized",
            "permission denied", "access denied", "error:", "fatal:",
          ];
          for (const indicator of errorIndicators) {
            if (lower.includes(indicator)) {
              return { passed: false, action: "block", reason: `exec_command output contains error: "${indicator}"` };
            }
          }
        }
        if (!success && !error && !output) {
          return {
            passed: false, action: "block",
            reason: "exec_command failed with no error message",
          };
        }
      }

      // write_file / edit_file: success but no confirmation in output
      if ((name === "write_file" || name === "edit_file")) {
        if (success && !output) {
          return {
            passed: false, action: "block",
            reason: `${name} reported success but produced no output confirmation`,
          };
        }
      }

      // search_files / search_content: empty results might be suspicious
      // But they're often legitimate — just flag for awareness
      // (No blocking, just a note in the result)

      return { passed: true, action: "allow" };
    },
  };
}
