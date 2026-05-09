"""Tool System — 借鉴 OpenClaw ToolDescriptor + Hermes 工具注册

ToolDescriptor: 静态元数据 (name, description, inputSchema, executor, availability)
ToolExecutorRef: bash / browser / file / session
ToolAvailability: 布尔条件 (auth, config, sandbox, plugin)
Parallel safety: 安全工具可并行, 破坏性工具串行
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolExecutorKind(Enum):
    BASH = "bash"
    BROWSER = "browser"
    FILE = "file"
    SESSION = "session"


class TrustLevel(Enum):
    OWNER = "owner"
    APPROVED = "approved"
    GUEST = "guest"
    GROUP = "group"


@dataclass
class ToolAvailability:
    """工具可用性条件 (布尔逻辑)。"""
    requires_auth: bool = False
    requires_config: list[str] = field(default_factory=list)
    sandbox_only: bool = False
    min_trust: TrustLevel = TrustLevel.GUEST

    def check(self, trust: TrustLevel, config: dict, is_sandboxed: bool = False) -> bool:
        if self.requires_auth and not config.get("auth_enabled"):
            return False
        for key in self.requires_config:
            if key not in config:
                return False
        if self.sandbox_only and not is_sandboxed:
            return False
        # TrustLevel ordering: OWNER > APPROVED > GUEST > GROUP
        trust_order = {TrustLevel.OWNER: 3, TrustLevel.APPROVED: 2,
                       TrustLevel.GUEST: 1, TrustLevel.GROUP: 0}
        return trust_order.get(trust, 0) >= trust_order.get(self.min_trust, 0)


@dataclass
class ToolDescriptor:
    """工具的静态描述。"""
    name: str
    description: str
    executor: ToolExecutorKind
    input_schema: dict = field(default_factory=dict)
    availability: ToolAvailability = field(default_factory=ToolAvailability)
    parallel_safe: bool = False
    destructive: bool = False
    executor_class: str = ""          # 执行器类名 (LocalBashExecutor / FileReadExecutor 等)
    timeout_seconds: float = 30.0     # 超时秒数
    audit_level: str = "basic"       # none / basic / full

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "executor": self.executor.value,
            "input_schema": self.input_schema,
        }

    def to_prompt(self) -> str:
        """生成可注入系统提示的工具描述。"""
        return f"- {self.name}: {self.description}"


class ToolRegistry:
    """工具注册表 (借鉴 Hermes tools/registry.py)。"""

    def __init__(self):
        self._tools: dict[str, ToolDescriptor] = {}

    def register(self, tool: ToolDescriptor):
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDescriptor | None:
        return self._tools.get(name)

    def list_available(self, trust: TrustLevel, config: dict,
                       is_sandboxed: bool = False) -> list[ToolDescriptor]:
        return [t for t in self._tools.values()
                if t.availability.check(trust, config, is_sandboxed)]

    def build_tool_prompt(self, trust: TrustLevel, config: dict,
                          is_sandboxed: bool = False) -> str:
        available = self.list_available(trust, config, is_sandboxed)
        if not available:
            return "无可用工具。"
        lines = ["## 可用工具", ""]
        for t in available:
            lines.append(t.to_prompt())
        return "\n".join(lines)

    def get_parallel_safe(self) -> set[str]:
        return {t.name for t in self._tools.values() if t.parallel_safe}


# ── 内置工具注册 ──

def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    # Bash 工具 (仅 owner)
    registry.register(ToolDescriptor(
        name="bash",
        description="执行 shell 命令。返回 stdout/stderr。",
        executor=ToolExecutorKind.BASH,
        input_schema={"type": "object", "required": ["command"],
                      "properties": {"command": {"type": "string"}}},
        availability=ToolAvailability(min_trust=TrustLevel.OWNER, sandbox_only=True),
        destructive=True,
        executor_class="LocalBashExecutor",
        timeout_seconds=30.0,
        audit_level="full",
    ))

    # File 读
    registry.register(ToolDescriptor(
        name="file_read",
        description="读取文件内容。",
        executor=ToolExecutorKind.FILE,
        input_schema={"type": "object", "required": ["path"],
                      "properties": {"path": {"type": "string"}}},
        availability=ToolAvailability(min_trust=TrustLevel.APPROVED),
        parallel_safe=True,
        executor_class="FileReadExecutor",
        timeout_seconds=5.0,
    ))

    # File 写 (仅 owner)
    registry.register(ToolDescriptor(
        name="file_write",
        description="写入文件。",
        executor=ToolExecutorKind.FILE,
        input_schema={"type": "object", "required": ["path", "content"],
                      "properties": {"path": {"type": "string"}, "content": {"type": "string"}}},
        availability=ToolAvailability(min_trust=TrustLevel.OWNER, sandbox_only=True),
        destructive=True,
        executor_class="FileWriteExecutor",
        timeout_seconds=10.0,
        audit_level="full",
    ))

    # Session 工具 (所有信任级别)
    for st in ["sessions_list", "sessions_send", "sessions_history", "sessions_spawn"]:
        registry.register(ToolDescriptor(
            name=st,
            description=f"会话工具: {st}。",
            executor=ToolExecutorKind.SESSION,
            availability=ToolAvailability(min_trust=TrustLevel.GUEST),
            parallel_safe=(st != "sessions_send"),
        ))

    # 记忆搜索 (所有信任级别)
    registry.register(ToolDescriptor(
        name="memory_search",
        description="搜索角色记忆。",
        executor=ToolExecutorKind.FILE,
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        availability=ToolAvailability(min_trust=TrustLevel.GUEST),
        parallel_safe=True,
    ))

    return registry
