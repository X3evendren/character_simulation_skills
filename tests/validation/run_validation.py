#!/usr/bin/env python
"""心理学真值验证运行器。

用法:
    python -m tests.validation.run_validation [--quality Q]

输出分层评分报告，识别系统在心理学准确性上的薄弱点。
"""
from __future__ import annotations

import asyncio
import argparse
import sys
import os

# Ensure package importable (go 4 levels up from run_validation.py to reach the repo parent)
_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from character_mind.tests.validation.validator import run_all


def main():
    parser = argparse.ArgumentParser(description="Psychology Validation Runner")
    parser.add_argument("--quality", type=float, default=1.0,
                        help="Mock provider quality (default: 1.0 = perfect JSON)")
    args = parser.parse_args()

    result = asyncio.run(run_all(quality=args.quality))

    # 返回非零退出码如果有薄弱点
    weak_count = sum(
        1 for s, i in result["aggregation"]["by_skill"].items() if i["score"] < 0.4
    )
    if weak_count > 0:
        print(f"\n{weak_count} Skill得分严重不足, 需要改进。")
        sys.exit(1)


if __name__ == "__main__":
    main()
