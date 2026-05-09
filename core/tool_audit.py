"""Tool Audit — 工具执行审计日志。

环形缓冲区存储审计条目，支持按会话/工具名/时间范围查询。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AuditEntry:
    """单条审计记录。"""
    tool_name: str
    session_id: str
    params_hash: str       # 参数内容的 SHA256 前 8 位
    success: bool
    duration_ms: float
    timestamp: float
    error: str = ""
    sandbox_type: str = "none"

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "session_id": self.session_id,
            "params_hash": self.params_hash,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "error": self.error,
            "sandbox_type": self.sandbox_type,
        }


@dataclass
class AuditLog:
    """工具执行审计日志——环形缓冲区。"""

    max_entries: int = 1000
    _entries: list[AuditEntry] = field(default_factory=list)
    _write_pos: int = 0

    def record(
        self, tool_name: str, session_id: str, params: dict,
        success: bool, duration_ms: float, error: str = "",
        sandbox_type: str = "none",
    ) -> None:
        """记录一次工具执行。"""
        import hashlib
        params_str = str(sorted(params.items())) if params else ""
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:8]

        entry = AuditEntry(
            tool_name=tool_name,
            session_id=session_id,
            params_hash=params_hash,
            success=success,
            duration_ms=duration_ms,
            timestamp=time.time(),
            error=error,
            sandbox_type=sandbox_type,
        )

        if len(self._entries) < self.max_entries:
            self._entries.append(entry)
        else:
            self._entries[self._write_pos] = entry
            self._write_pos = (self._write_pos + 1) % self.max_entries

    def query(
        self, tool_name: str | None = None, session_id: str | None = None,
        since: float = 0.0, limit: int = 50,
    ) -> list[AuditEntry]:
        """查询审计记录。"""
        results = []
        for entry in reversed(self._entries):
            if tool_name and entry.tool_name != tool_name:
                continue
            if session_id and entry.session_id != session_id:
                continue
            if since and entry.timestamp < since:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def stats(self) -> dict:
        """审计统计。"""
        if not self._entries:
            return {"total": 0, "success_rate": 0.0}
        total = len(self._entries)
        success_count = sum(1 for e in self._entries if e.success)
        tool_counts: dict[str, int] = {}
        total_duration = 0.0
        for e in self._entries:
            tool_counts[e.tool_name] = tool_counts.get(e.tool_name, 0) + 1
            total_duration += e.duration_ms
        return {
            "total": total,
            "success_rate": success_count / total if total else 0.0,
            "by_tool": tool_counts,
            "avg_duration_ms": total_duration / total if total else 0.0,
        }

    def clear(self) -> None:
        self._entries.clear()
        self._write_pos = 0

    def to_dict(self) -> list[dict]:
        return [e.to_dict() for e in self._entries]
