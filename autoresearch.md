# Autoresearch: Token Efficiency + TOCA + Multi-Agent Optimization

## Objective
Optimize token efficiency (tokens per pipeline event), TOCA write success rate, and multi-agent response consistency. Primary focus on reducing tokens while maintaining or improving response quality.

## Metrics
- **Primary**: total_tokens (count, lower is better) — total tokens consumed per pipeline event
- **Secondary**: response_quality (fraction, higher is better) — response_generator produces non-empty text
- **Secondary**: multi_agent_continuity (fraction, higher is better) — emotion consistency across turns

## How to Run
`./autoresearch.sh` — outputs `METRIC name=number` lines.

## Files in Scope
- `skills/*/` — all Skill prompt files (token reduction via prompt shortening)
- `core/orchestrator.py` — pipeline efficiency
- `skills/l5_state_update/response_generator.py` — response quality
- `core/base.py` — extract_json already optimized, don't touch

## Off Limits
- `benchmark/` — benchmark infrastructure
- `tests/` — test infrastructure  
- `core/blackboard.py` — stable core
- `extract_json()` in core/base.py — already optimal

## Constraints
- All skills must continue to function (parse_success=True)
- Response text must remain non-empty (quality must not degrade)
- No new dependencies
- Backward compatible API

## What's Been Tried
(New session — baseline pending)
