"""Tool Executor — 工具执行引擎。

提供本地 Bash、文件读写等执行器，带超时保护、沙箱路由和中间件链。
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any

from .tool_middleware import (
    ToolMiddleware, ToolContext,
    PathSafetyMiddleware, AuditLoggingMiddleware,
    RateLimitMiddleware, ParameterValidationMiddleware,
)
from .tool_audit import AuditLog


@dataclass
class ToolResult:
    """工具执行结果。"""
    success: bool
    output: str
    error: str = ""
    execution_time: float = 0.0
    audit_id: str = ""
    exit_code: int = 0
    truncated: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "audit_id": self.audit_id,
            "exit_code": self.exit_code,
            "truncated": self.truncated,
        }


class BaseToolExecutor(ABC):
    """工具执行器抽象基类。"""

    @abstractmethod
    async def execute(
        self, tool_name: str, params: dict, context: ToolContext,
    ) -> ToolResult:
        ...


# ── 内建执行器 ──


@dataclass
class LocalBashExecutor(BaseToolExecutor):
    """本地 Bash 执行器——通过 asyncio subprocess 执行命令。"""

    work_dir: str = ""
    timeout_seconds: float = 30.0
    max_output_chars: int = 10000
    allowed_commands: list[str] | None = None  # None = 允许一切
    blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /", "mkfs.", "dd if=", ":(){ :|:& };:",
        "shutdown", "reboot", "poweroff",
    ])

    async def execute(
        self, tool_name: str, params: dict, context: ToolContext,
    ) -> ToolResult:
        command = params.get("command", params.get("cmd", ""))
        if not command:
            return ToolResult(False, "", "没有提供命令", audit_id=str(uuid.uuid4())[:8])

        # 安全检查
        cmd_lower = command.lower()
        for blocked in self.blocked_commands:
            if blocked.lower() in cmd_lower:
                return ToolResult(
                    False, "", f"命令被阻止: 匹配危险模式 '{blocked}'",
                    audit_id=str(uuid.uuid4())[:8],
                )

        if self.allowed_commands is not None:
            if not any(allowed.lower() in cmd_lower for allowed in self.allowed_commands):
                return ToolResult(
                    False, "", "命令不在允许列表中",
                    audit_id=str(uuid.uuid4())[:8],
                )

        audit_id = str(uuid.uuid4())[:8]
        start = time.time()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.work_dir or os.getcwd(),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout_seconds,
            )
            elapsed = time.time() - start

            output = (stdout or b"").decode("utf-8", errors="replace")
            err_output = (stderr or b"").decode("utf-8", errors="replace")
            truncated = False

            if len(output) > self.max_output_chars:
                output = output[:self.max_output_chars] + "\n... [truncated]"
                truncated = True

            combined = output
            if err_output:
                combined += f"\n[stderr]\n{err_output}"

            return ToolResult(
                success=proc.returncode == 0,
                output=combined.strip() or "(no output)",
                error=err_output.strip() if proc.returncode != 0 else "",
                execution_time=elapsed,
                audit_id=audit_id,
                exit_code=proc.returncode or 0,
                truncated=truncated,
            )
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            return ToolResult(
                False, "", f"命令超时 ({self.timeout_seconds}s)",
                execution_time=elapsed, audit_id=audit_id,
            )
        except Exception as e:
            elapsed = time.time() - start
            return ToolResult(
                False, "", str(e),
                execution_time=elapsed, audit_id=audit_id,
            )


@dataclass
class FileReadExecutor(BaseToolExecutor):
    """文件读取执行器——带路径遍历保护。"""

    allowed_base_dir: str = ""

    async def execute(
        self, tool_name: str, params: dict, context: ToolContext,
    ) -> ToolResult:
        path = params.get("path", params.get("file_path", ""))
        if not path:
            return ToolResult(False, "", "没有提供文件路径")

        start = time.time()

        try:
            abs_path = os.path.abspath(path)
            if self.allowed_base_dir:
                if not abs_path.startswith(os.path.abspath(self.allowed_base_dir)):
                    return ToolResult(False, "", f"路径越界: {path}")

            if not os.path.exists(abs_path):
                return ToolResult(False, "", f"文件不存在: {path}",
                                  execution_time=time.time() - start)

            if os.path.getsize(abs_path) > 10 * 1024 * 1024:  # 10MB
                return ToolResult(False, "", "文件过大 (max 10MB)",
                                  execution_time=time.time() - start)

            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(50000)  # 最多读 50KB

            return ToolResult(
                success=True, output=content,
                execution_time=time.time() - start,
                audit_id=str(uuid.uuid4())[:8],
            )
        except Exception as e:
            return ToolResult(
                False, "", str(e),
                execution_time=time.time() - start,
                audit_id=str(uuid.uuid4())[:8],
            )


@dataclass
class FileWriteExecutor(BaseToolExecutor):
    """文件写入执行器——带路径遍历保护。"""

    allowed_base_dir: str = ""

    async def execute(
        self, tool_name: str, params: dict, context: ToolContext,
    ) -> ToolResult:
        path = params.get("path", params.get("file_path", ""))
        content = params.get("content", "")
        if not path:
            return ToolResult(False, "", "没有提供文件路径")

        start = time.time()

        try:
            abs_path = os.path.abspath(path)
            if self.allowed_base_dir:
                if not abs_path.startswith(os.path.abspath(self.allowed_base_dir)):
                    return ToolResult(False, "", f"路径越界: {path}")

            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"写入 {len(content)} 字符到 {path}",
                execution_time=time.time() - start,
                audit_id=str(uuid.uuid4())[:8],
            )
        except Exception as e:
            return ToolResult(
                False, "", str(e),
                execution_time=time.time() - start,
                audit_id=str(uuid.uuid4())[:8],
            )


# ── 执行器工厂 ──


class ToolExecutorFactory:
    """根据工具描述中的 executor_class 创建执行器。"""

    _registry: dict[str, type[BaseToolExecutor]] = {
        "LocalBashExecutor": LocalBashExecutor,
        "FileReadExecutor": FileReadExecutor,
        "FileWriteExecutor": FileWriteExecutor,
    }

    @classmethod
    def register(cls, name: str, executor_cls: type[BaseToolExecutor]) -> None:
        cls._registry[name] = executor_cls

    @classmethod
    def create(cls, executor_class: str, **kwargs) -> BaseToolExecutor | None:
        """创建执行器实例。"""
        ec = cls._registry.get(executor_class)
        if ec is None:
            return None
        return ec(**kwargs)

    @classmethod
    def list_registered(cls) -> list[str]:
        return list(cls._registry.keys())


# ── 中间件链执行包装 ──


@dataclass
class ToolExecutionChain:
    """工具执行链——中间件 + 执行器。

    流程: before chain → execute → after chain (reverse order)
    """

    executor_factory: ToolExecutorFactory = field(default_factory=ToolExecutorFactory)
    middlewares: list[ToolMiddleware] = field(default_factory=list)

    def add_middleware(self, mw: ToolMiddleware) -> None:
        self.middlewares.append(mw)

    async def execute(
        self, descriptor, params: dict, context: ToolContext,
    ) -> ToolResult:
        """执行工具：运行中间件 before 链 → 执行 → after 链。"""
        tool_name = descriptor.name if hasattr(descriptor, "name") else str(descriptor)

        # Before 链
        for mw in self.middlewares:
            allowed, reason = await mw.before(tool_name, params, context)
            if not allowed:
                return ToolResult(
                    False, "", f"被 {mw.__class__.__name__} 拒绝: {reason}",
                    audit_id=str(uuid.uuid4())[:8],
                )

        # 创建执行器
        executor_class = getattr(descriptor, "executor_class", "") or "LocalBashExecutor"
        executor = self.executor_factory.create(executor_class)
        if executor is None:
            return ToolResult(False, "", f"未找到执行器: {executor_class}")

        # 执行
        result = await executor.execute(tool_name, params, context)

        # After 链（逆序）
        for mw in reversed(self.middlewares):
            result_dict = result.to_dict()
            modified = await mw.after(tool_name, params, result_dict, context)
            if modified != result_dict:
                result = ToolResult(**modified)

        return result


def build_default_chain(audit_log: AuditLog | None = None,
                        allowed_dirs: list[str] | None = None) -> ToolExecutionChain:
    """构建默认工具执行链。"""
    chain = ToolExecutionChain()

    # 路径安全
    path_mw = PathSafetyMiddleware()
    if allowed_dirs:
        for d in allowed_dirs:
            path_mw.add_allowed_dir(d)
    chain.add_middleware(path_mw)

    # 速率限制
    rate_mw = RateLimitMiddleware()
    rate_mw.set_limit("bash", 30)
    rate_mw.set_limit("file_write", 60)
    chain.add_middleware(rate_mw)

    # 审计日志
    if audit_log:
        chain.add_middleware(AuditLoggingMiddleware(audit_log=audit_log))

    return chain
