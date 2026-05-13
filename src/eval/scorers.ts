/**
 * Step-level scoring functions for eval behaviors.
 * Each scorer takes the agent output + expected behavior and returns pass/fail + actual value.
 */
import type { ExpectedBehavior } from "./golden-dataset";

export interface ScoreResult {
  passed: boolean;
  actual: string;
  score: number; // 0-1 weighted
}

export interface EvalAgentOutput {
  response: string;
  toolCalls: string[];
  totalTokens: number;
}

export function scoreBehavior(output: EvalAgentOutput, behavior: ExpectedBehavior): ScoreResult {
  switch (behavior.type) {
    case "contains": return scoreContains(output.response, behavior.target, behavior.weight);
    case "not_contains": return scoreNotContains(output.response, behavior.target, behavior.weight);
    case "matches": return scoreMatches(output.response, behavior.target, behavior.weight);
    case "tool_called": return scoreToolCalled(output.toolCalls, behavior.target, behavior.weight);
    case "no_tool_called": return scoreNoToolCalled(output.toolCalls, behavior.target, behavior.weight);
    case "max_tokens": return scoreMaxTokens(output.totalTokens, parseInt(behavior.target) || 500, behavior.weight);
    default: return { passed: false, actual: "unknown behavior type", score: 0 };
  }
}

function scoreContains(text: string, target: string, weight: number): ScoreResult {
  const passed = text.includes(target);
  return { passed, actual: passed ? `found "${target}"` : `"${target}" not found`, score: passed ? weight : 0 };
}

function scoreNotContains(text: string, target: string, weight: number): ScoreResult {
  const passed = !text.includes(target);
  return { passed, actual: passed ? `"${target}" absent` : `"${target}" present`, score: passed ? weight : 0 };
}

function scoreMatches(text: string, pattern: string, weight: number): ScoreResult {
  try {
    const re = new RegExp(pattern, "i");
    const passed = re.test(text);
    return { passed, actual: passed ? `matched /${pattern}/` : `no match for /${pattern}/`, score: passed ? weight : 0 };
  } catch {
    return { passed: false, actual: `invalid regex: ${pattern}`, score: 0 };
  }
}

function scoreToolCalled(toolCalls: string[], toolName: string, weight: number): ScoreResult {
  const passed = toolCalls.includes(toolName);
  return { passed, actual: passed ? `tool "${toolName}" called` : `tool "${toolName}" NOT called (called: ${toolCalls.join(", ") || "none"})`, score: passed ? weight : 0 };
}

function scoreNoToolCalled(toolCalls: string[], toolName: string, weight: number): ScoreResult {
  const passed = !toolCalls.includes(toolName);
  return { passed, actual: passed ? `tool "${toolName}" not called` : `tool "${toolName}" was called`, score: passed ? weight : 0 };
}

function scoreMaxTokens(actual: number, limit: number, weight: number): ScoreResult {
  const passed = actual <= limit;
  return { passed, actual: `${actual} tokens (limit: ${limit})`, score: passed ? weight : 0 };
}
