# Autoresearch Worklog: Token Efficiency + TOCA + Multi-Agent

**Start:** 2026-05-06
**Branch:** autoresearch/token-efficiency-2026-05-06
**Primary Metric:** total_tokens (count, lower is better)

---

## Baseline

### Run 1: baseline — total_tokens=9052.3 (keep)
- Timestamp: 2026-05-06
- What changed: Initial state — 22 skills, 5-layer pipeline, TOCA integrated
- Result: total_tokens=9052.3, toca_write_rate=1.00, response_quality=1.00, multi_agent_continuity=1.00
- Insight: Token budget: L0 ~1200, L1 ~1800, L2 ~2400, L3 ~1800, L4 ~800, L5 ~1000. L2 (4 skills) and L3 (trigger-dependent) are the biggest consumers.
- Next: Shorten L2 skill prompts (occ_emotion, smith_ellsworth) — they have the longest prompts

---

## Key Insights
- L2 skills consume ~27% of total tokens (4 skills, each with extensive theory explanations in prompt)
- Smith-Ellsworth and OCC have the longest prompts
- TOCA write rate already at 1.00 — focus on token reduction

## Next Ideas
- Shorten Smith-Ellsworth prompt (16-dim explanation is verbose)
- Shorten OCC emotion prompt (6 appraisal dimensions could be more concise)  
- Remove redundant "你是XX专家" prefixes from skill prompts
- Use shorter JSON field names in skill outputs
- Merge plutchik + emotion_probe L1 calls (they overlap)
