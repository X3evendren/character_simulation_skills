# Autoresearch: JSON Parse Quality Optimization

## Objective
Improve the robustness of the character simulation skills system's JSON parsing pipeline. The mock LLM provider simulates realistic but imperfect output (quality=0.6), and we optimize `extract_json()`, `parse_output()`, and error handling to maximize the rate of successful JSON extraction.

## Metrics
- **Primary**: json_parse_rate (fraction, higher is better) — fraction of skill executions where extract_json() successfully parses LLM output beyond minimal fallback
- **Secondary**: field_coverage (fraction, higher is better) — fraction of expected output fields actually present
- **Secondary**: total_tokens (count, lower is better) — total tokens consumed across all skills
- **Secondary**: skill_error_rate (fraction, lower is better) — fraction of skills that threw exceptions

## How to Run
`./autoresearch.sh` — outputs `METRIC name=number` lines.

## Files in Scope
- `base.py` — `extract_json()` function, `BaseSkill.run()` method, `SkillResult` dataclass
- Individual skill files' `parse_output()` methods — all files under the package root matching *.py
- Individual skill files' `build_prompt()` methods — for token optimization and output format enforcement
- `orchestrator.py` — `CognitiveOrchestrator` pipeline, retry logic opportunities

## Off Limits
- `benchmark/` directory — benchmark infrastructure, not to be optimized
- `素材/` directory — reference materials
- Skill scientific content — don't change what models analyze, only how outputs are parsed

## Constraints
- All existing tests (none) must pass
- No new dependencies
- Must maintain backward compatibility with existing SkillResult interface
- Skills must continue to function when extract_json fails (fallback required)

## What's Been Tried
(Will be updated as experiments accumulate)
