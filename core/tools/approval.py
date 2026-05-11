"""工具审批 + 护栏 — 抄 Hermes Agent approval.py + guardrails。

- 审批系统: 正则模式匹配 + 危险命令检测
- 护栏: 防重复调用 / 防连续失败循环
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field


# 危险 Shell 模式 — 抄 Hermes + Claude Code
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-rf\s+/", "递归删除根目录"),
    (r"dd\s+if=", "磁盘直接写入"),
    (r"mkfs\.", "格式化文件系统"),
    (r">\s*/dev/sd", "写入块设备"),
    (r"chmod\s+777", "过度放宽权限"),
    (r"curl.*\|.*sh", "管道执行远程脚本"),
    (r"wget.*\|.*sh", "管道执行远程脚本"),
    (r"eval\s", "eval 命令执行"),
    (r"sudo\s", "特权提升"),
    (r"git\s+push\s+--force", "强制推送"),
    (r"git\s+reset\s+--hard", "硬重置"),
]


@dataclass
class ApprovalResult:
    """审批结果"""
    allowed: bool = True
    reason: str = ""
    requires_user: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class CallRecord:
    """工具调用记录——用于护栏检测"""
    tool_name: str
    params_hash: str
    success: bool
    timestamp: float


class ApprovalSystem:
    """工具审批系统 — 抄 Hermes approval.py。

    检查顺序:
    1. 风险等级检查 (low → 自动通过)
    2. 危险模式匹配 (正则)
    3. 需要用户确认 (high risk)
    """

    @staticmethod
    def check(tool_name: str, params: dict, risk_level: str = "low") -> ApprovalResult:
        result = ApprovalResult()

        if risk_level == "low":
            return result

        # 检查命令参数中的危险模式
        command = params.get("command", "")
        if command:
            for pattern, description in DANGEROUS_PATTERNS:
                if re.search(pattern, command):
                    result.allowed = False
                    result.reason = f"危险命令: {description}"
                    result.warnings.append(description)
                    return result

        if risk_level == "high":
            result.requires_user = True
            result.warnings.append("高风险操作，建议用户确认")

        return result


class ToolGuardrails:
    """工具护栏 — 防重复调用 / 防连续失败。

    抄 Hermes Agent tool_guardrails.py 的设计:
    - 相同参数重复调用: 警告
    - 同一工具连续失败: 阻止
    """

    def __init__(self, max_consecutive_failures: int = 3):
        self.max_consecutive_failures = max_consecutive_failures
        self._call_history: list[CallRecord] = []
        self._failure_counts: dict[str, int] = {}

    def record_call(self, tool_name: str, params: dict, success: bool):
        import hashlib, json
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()

        self._call_history.append(CallRecord(
            tool_name=tool_name, params_hash=params_hash,
            success=success, timestamp=time.time(),
        ))

        if not success:
            self._failure_counts[tool_name] = self._failure_counts.get(tool_name, 0) + 1
        else:
            self._failure_counts[tool_name] = 0

        # 清理旧记录
        if len(self._call_history) > 100:
            self._call_history = self._call_history[-100:]

    def check_duplicate(self, tool_name: str, params: dict) -> tuple[bool, str]:
        """检查是否与最近调用完全相同（防循环）。"""
        import hashlib, json
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()

        recent = [c for c in self._call_history[-10:]
                  if c.tool_name == tool_name and c.params_hash == params_hash]

        if len(recent) >= 3:
            return True, f"工具 {tool_name} 相同参数已调用 {len(recent)} 次，建议停止"
        if len(recent) >= 1:
            return False, f"工具 {tool_name} 相同参数刚调用过"
        return False, ""

    def check_consecutive_failures(self, tool_name: str) -> tuple[bool, str]:
        """检查是否连续失败超过阈值。"""
        count = self._failure_counts.get(tool_name, 0)
        if count >= self.max_consecutive_failures:
            return True, f"工具 {tool_name} 连续失败 {count} 次，已阻止调用"
        return False, ""
