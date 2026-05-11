"""工具系统 — Tool ABC + ToolRegistry + Schema Builder。

抄 nanobot agent/tools/base.py 的 Tool 抽象基类设计。
抄 nanobot agent/tools/registry.py 的 ToolRegistry 注册表设计。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """工具执行结果"""
    name: str = ""
    output: str = ""
    error: str = ""
    success: bool = True


class Tool(ABC):
    """工具抽象基类 — 抄 nanobot agent/tools/base.py。

    每个工具必须定义: name, description, parameters (JSON Schema), execute()
    """

    name: str = ""
    description: str = ""
    parameters: dict = field(default_factory=dict)  # JSON Schema
    is_read_only: bool = True
    is_concurrency_safe: bool = True
    risk_level: str = "low"  # low / medium / high

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具。"""
        ...

    def to_openai_schema(self) -> dict:
        """导出为 OpenAI function calling 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate_params(self, **kwargs) -> dict | None:
        """简易参数验证。返回错误信息或 None。"""
        required = []
        if isinstance(self.parameters, dict):
            required = self.parameters.get("required", [])
            properties = self.parameters.get("properties", {})
            for key in required:
                if key not in kwargs or kwargs[key] is None:
                    return {"error": f"缺少必需参数: {key}"}
        return None


class ToolRegistry:
    """工具注册表 — 抄 nanobot agent/tools/registry.py。

    管理工具生命周期: 注册/注销/发现/执行。
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_definitions(self) -> list[dict]:
        """导出所有工具为 OpenAI function schema 列表。"""
        return [t.to_openai_schema() for t in self._tools.values()]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    async def execute(self, name: str, params: dict) -> ToolResult:
        """执行工具调用。

        包含: 工具查找 → 参数验证 → 执行 → 错误处理。
        """
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(name=name, success=False, error=f"工具不存在: {name}")

        # 参数验证
        validation_error = tool.validate_params(**params)
        if validation_error:
            return ToolResult(name=name, success=False, error=validation_error.get("error", "验证失败"))

        try:
            return await tool.execute(**params)
        except Exception as e:
            return ToolResult(name=name, success=False, error=str(e))

    def risk_summary(self) -> dict[str, int]:
        """按风险等级统计工具数量。"""
        summary = {"low": 0, "medium": 0, "high": 0}
        for t in self._tools.values():
            summary[t.risk_level] = summary.get(t.risk_level, 0) + 1
        return summary

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
