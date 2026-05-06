# Autoresearch Dashboard: json-parse-quality

**Runs:** 2 | **Kept:** 2 | **Discarded:** 0 | **Crashed:** 0
**Baseline:** json_parse_rate: 0.5707 (#1)
**Best:** json_parse_rate: 0.6299 (#2, +10.4%)

| # | commit | json_parse_rate | field_coverage | total_tokens | status | description |
|---|--------|-----------------|----------------|-------------|--------|-------------|
| 1 | 1beebe3 | 0.5707 | 0.7030 | 9009.6 | keep | baseline |
| 2 | a16bec6 | 0.6299 (+10.4%) | 0.7076 | 8978.8 | keep | trailing comma and BOM handling in extract_json |
