#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python benchmark/run_benchmark.py --quality 0.35 --scenarios 0 "$@"
