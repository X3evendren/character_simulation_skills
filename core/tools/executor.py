"""工具执行器 — 抄 Claude Code toolExecution.ts + toolOrchestration.ts。

流程: validateInput → permission → call → postHooks
并发: 只读(并行) vs 写(串行)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .base import ToolRegistry, ToolResult, Tool


@dataclass
class AuditResult:
    """命令审计结果"""
    allowed: bool = True
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)
    reason: str = ""


def partition_calls(tool_calls: list[dict], registry: ToolRegistry
                    ) -> tuple[list[dict], list[dict]]:
    """将工具调用分为并行批和串行批。

    抄 Claude Code partitionToolCalls():
    - isConcurrencySafe → 并行
    - !isConcurrencySafe → 串行
    """
    parallel = []
    serial = []
    for tc in tool_calls:
        tool = registry.get(tc["name"])
        if tool and getattr(tool, 'is_concurrency_safe', True):
            parallel.append(tc)
        else:
            serial.append(tc)
    return parallel, serial


async def run_one(name: str, params: dict, registry: ToolRegistry
                  ) -> ToolResult:
    """执行单个工具调用。

    抄 Claude Code runToolUse():
    validateInput → permission check → call → result
    """
    tool = registry.get(name)
    if not tool:
        return ToolResult(name=name, success=False, error=f"工具不存在: {name}")

    # 参数验证
    err = tool.validate_params(**params)
    if err:
        return ToolResult(name=name, success=False, error=err.get("error", "参数验证失败"))

    # 执行
    try:
        return await tool.execute(**params)
    except Exception as e:
        return ToolResult(name=name, success=False, error=str(e))


async def execute_parallel(calls: list[dict], registry: ToolRegistry
                           ) -> list[ToolResult]:
    """并行执行只读工具调用。"""
    tasks = [run_one(c["name"], c.get("arguments", {}), registry) for c in calls]
    return await asyncio.gather(*tasks)


async def execute_serial(calls: list[dict], registry: ToolRegistry
                         ) -> list[ToolResult]:
    """串行执行写工具调用。"""
    results = []
    for c in calls:
        r = await run_one(c["name"], c.get("arguments", {}), registry)
        results.append(r)
        if not r.success:
            break  # 写操作失败 → 停止后续
    return results


async def execute_all(calls: list[dict], registry: ToolRegistry
                      ) -> list[ToolResult]:
    """执行全部工具调用——先并行(只读)后串行(写)。

    抄 Claude Code runTools()。
    """
    parallel, serial = partition_calls(calls, registry)

    results = []
    if parallel:
        results.extend(await execute_parallel(parallel, registry))
    if serial:
        results.extend(await execute_serial(serial, registry))

    return results
