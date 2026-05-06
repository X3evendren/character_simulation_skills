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

### Run 2: trailing comma and BOM handling in extract_json — json_parse_rate=0.6299 (KEEP, +10.4%)
- Timestamp: 2026-05-06
- What changed: Added `text.lstrip("﻿​...")` for BOM/zero-width removal and `re.sub(r',\s*([]}])', r'\1', text)` for trailing comma removal before `json.loads()`
- Result: json_parse_rate=0.6299 (+10.4%), field_coverage=0.7076 (+0.7%), total_tokens=8978.8 (-0.3%)
- Insight: Trailing commas are a common LLM mistake at quality=0.6. Simple regex cleanup recovers ~6 percentage points of parse rate. BOM removal had minimal impact but is free.
- Next: Add single-quote JSON handling

---

## Key Insights
- Trailing commas account for ~10% of parse failures at quality=0.6 — a simple regex fix recovers them
- The anti-alignment hint prepended to prompts contains psychological terms that can confuse output detection
- Fallback outputs make it impossible to distinguish parse failures from empty-but-valid results without field-level comparison

## Next Ideas
- Handle single-quoted JSON keys/values (replace ' with " before parsing)
- Strip extra text before/after JSON more aggressively
- Attempt partial recovery from truncated JSON (add missing closing braces)
- Add retry prompt in `BaseSkill.run()` when output is empty/malformed
- Enforce stricter JSON format in skill prompts (add "ONLY output JSON" instructions)
