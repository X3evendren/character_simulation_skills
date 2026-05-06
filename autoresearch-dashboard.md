# Autoresearch Dashboard: json-parse-quality

**Runs:** 12 | **Kept:** 9 | **Discarded:** 3

## Segment 0 (original metric)
**Baseline:** json_parse_rate: 0.5707 (#1)
**Best:** json_parse_rate: 0.7755 (#6, +35.9%)

| # | commit | json_parse_rate | field_coverage | status | description |
|---|--------|-----------------|----------------|--------|-------------|
| 1 | 1beebe3 | 0.5707 | 0.7030 | keep | baseline |
| 2 | a16bec6 | 0.6299 | 0.7076 | keep | trailing comma + BOM handling |
| 3 | c01e60d | 0.7215 | 0.7346 | keep | single-quote JSON handling |
| 4 | a1e8d08 | 0.7120 | 0.7397 | discard | retry logic (RNG perturbation) |
| 5 | a1e8d08 | 0.7203 | 0.7592 | discard | smarter truncated recovery (regression) |
| 6 | 5583fa5 | 0.7755 | 0.7624 | keep | improved markdown fence extraction |
| 3 | a1e8d08 | 0.7500 | 0.7662 | keep | truncated JSON recovery |

## Segment 2 (parse_success metric)
**Baseline:** json_parse_rate: 0.8133 (#8), field_coverage: 0.7603
**Best:** json_parse_rate: 0.8216 (#9-12), field_coverage: 1.0000 (#12)

| # | commit | json_parse_rate | field_coverage | status | description |
|---|--------|-----------------|----------------|--------|-------------|
| 8 | e3b65b2 | 0.8133 | 0.7603 | keep | re-baseline: parse_success flag |
| 9 | 4cc69ea | 0.8216 | 0.7641 | keep | enhanced truncation recovery |
| 10 | d25d591 | 0.8216 | 0.8787 | keep | full defaults for 5 field-rich skills |
| 11 | dc852c3 | 0.8216 | 0.9425 | keep | full defaults for 5 more skills |
| 12 | 4f75402 | 0.8216 | 1.0000 | keep | full defaults for all 10 remaining skills |
