"""Tool Middleware — 工具执行中间件链。

每个中间件实现 before() / after() 钩子。
链按注册顺序执行：before() 可以拒绝执行，after() 可以修改结果。
"""
from __future__ import annotations

import time
import re
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any


@dataclass
class ToolContext:
    """工具执行的上下文信息。"""
    session_id: str = ""
    trust_level: str = "guest"
    is_sandboxed: bool = False
    call_depth: int = 0           # 嵌套调用深度
    parent_tool: str = ""         # 父工具名（如果是工具调用工具）


class ToolMiddleware(ABC):
    """工具中间件基类。"""

    @abstractmethod
    async def before(self, tool_name: str, params: dict,
                     context: ToolContext) -> tuple[bool, str]:
        """执行前检查。返回 (allowed, reason)。"""
        ...

    async def after(self, tool_name: str, params: dict,
                    result: dict, context: ToolContext) -> dict:
        """执行后处理。返回修改后的 result。"""
        return result


# ── 内建中间件 ──


@dataclass
class ParameterValidationMiddleware(ToolMiddleware):
    """参数验证中间件——根据 input_schema 验证参数。"""

    schemas: dict[str, dict] = field(default_factory=dict)

    def register_schema(self, tool_name: str, schema: dict) -> None:
        self.schemas[tool_name] = schema

    async def before(self, tool_name: str, params: dict,
                     context: ToolContext) -> tuple[bool, str]:
        schema = self.schemas.get(tool_name)
        if not schema:
            return True, ""  # 无 schema = 放行

        required = schema.get("required", [])
        for field in required:
            if field not in params or params[field] is None:
                return False, f"缺少必需参数: {field}"

        properties = schema.get("properties", {})
        for field, value in params.items():
            if field not in properties:
                continue
            prop = properties[field]
            expected_type = prop.get("type", "")
            if expected_type == "string" and not isinstance(value, str):
                return False, f"参数 {field} 应为字符串"
            if expected_type == "number" and not isinstance(value, (int, float)):
                return False, f"参数 {field} 应为数字"
            if expected_type == "integer" and not isinstance(value, int):
                return False, f"参数 {field} 应为整数"
            if expected_type == "boolean" and not isinstance(value, bool):
                return False, f"参数 {field} 应为布尔值"

        return True, ""


@dataclass
class AuditLoggingMiddleware(ToolMiddleware):
    """审计日志中间件——记录每次执行到审计日志。"""

    audit_log: Any = None  # AuditLog 实例

    async def before(self, tool_name: str, params: dict,
                     context: ToolContext) -> tuple[bool, str]:
        return True, ""  # 始终放行

    async def after(self, tool_name: str, params: dict,
                    result: dict, context: ToolContext) -> dict:
        if self.audit_log:
            self.audit_log.record(
                tool_name=tool_name,
                session_id=context.session_id,
                params=params,
                success=result.get("success", False),
                duration_ms=result.get("execution_time", 0) * 1000,
                error=result.get("error", ""),
                sandbox_type="docker" if context.is_sandboxed else "none",
            )
        return result


@dataclass
class RateLimitMiddleware(ToolMiddleware):
    """速率限制中间件——限制破坏性工具的调用频率。"""

    max_per_minute: dict[str, int] = field(default_factory=dict)
    _call_times: dict[str, list[float]] = field(default_factory=dict)

    def set_limit(self, tool_name: str, per_minute: int) -> None:
        self.max_per_minute[tool_name] = per_minute

    async def before(self, tool_name: str, params: dict,
                     context: ToolContext) -> tuple[bool, str]:
        limit = self.max_per_minute.get(tool_name)
        if not limit:
            return True, ""

        times = self._call_times.setdefault(tool_name, [])
        now = time.time()
        # 清理超过 1 分钟的记录
        times[:] = [t for t in times if now - t < 60]
        if len(times) >= limit:
            return False, f"速率限制: {tool_name} 每分钟最多 {limit} 次"
        times.append(now)
        return True, ""


@dataclass
class TimeoutMiddleware(ToolMiddleware):
    """超时控制中间件——但实际超时由执行器处理，这里仅记录。"""

    default_timeout: float = 30.0
    tool_timeouts: dict[str, float] = field(default_factory=dict)

    async def before(self, tool_name: str, params: dict,
                     context: ToolContext) -> tuple[bool, str]:
        return True, ""


@dataclass
class PathSafetyMiddleware(ToolMiddleware):
    """路径安全检查中间件——防止路径遍历攻击。"""

    allowed_dirs: list[str] = field(default_factory=list)

    async def before(self, tool_name: str, params: dict,
                     context: ToolContext) -> tuple[bool, str]:
        if tool_name not in ("file_read", "file_write"):
            return True, ""

        for key in ("path", "file_path", "target"):
            path = params.get(key, "")
            if not path:
                continue
            if _is_path_traversal(path):
                return False, f"路径遍历攻击检测: {path}"
            if self.allowed_dirs:
                import os
                abs_path = os.path.abspath(path)
                if not any(abs_path.startswith(d) for d in self.allowed_dirs):
                    return False, f"路径不在允许范围内: {path}"

        return True, ""

    def add_allowed_dir(self, directory: str) -> None:
        import os
        self.allowed_dirs.append(os.path.abspath(directory))


def _is_path_traversal(path: str) -> bool:
    """检测路径遍历攻击模式。"""
    return ".." in path or path.startswith("~") or path.startswith("/etc/")
