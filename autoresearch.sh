#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# LLM-as-Judge benchmark (DeepSeek V4 Pro thinking by default)
# Override with: --provider deepseek --think 0 for Flash mode
exec python benchmark/real_llm_benchmark.py --provider deepseek --think 1 "$@"
