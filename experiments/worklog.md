# Autoresearch Worklog: JSON Parse Quality Optimization

**Start:** 2026-05-06
**Branch:** autoresearch/json-parse-quality-2026-05-06
**Primary Metric:** json_parse_rate (fraction, higher is better)

---

## Baseline

### Run 1: baseline — json_parse_rate=0.5707 (keep)
- Timestamp: 2026-05-06 (start)
- What changed: Initial state — 21 skills, quality=0.6 mock provider
- Result: json_parse_rate=0.5707, field_coverage=0.7030, total_tokens=9009.6, skill_error_rate=0.0
- Insight: The current `extract_json()` handles markdown fences and bare JSON, but fails on trailing commas (common LLM mistake), single-quoted JSON, extra text after JSON, BOM characters, and truncated output. These failure modes account for ~43% of parse failures at quality=0.6.
- Next: Add trailing comma handling to `extract_json()`

---

## Key Insights
- The anti-alignment hint prepended to prompts contains psychological terms that can confuse output detection
- Fallback outputs make it impossible to distinguish parse failures from empty-but-valid results without field-level comparison
- At quality=0.6, ~43% of skill executions fail JSON parsing — the main failure modes are: trailing commas, single quotes, extra text after JSON, BOM, truncation

## Next Ideas
- Handle trailing commas in `extract_json()` (regex-based cleanup before json.loads)
- Handle single-quoted JSON keys/values
- Strip BOM and extra text before/after JSON
- Attempt partial recovery from truncated JSON
- Add retry prompt in `BaseSkill.run()` when output is empty/malformed
- Enforce stricter JSON format in skill prompts (add "ONLY output JSON" instructions)
