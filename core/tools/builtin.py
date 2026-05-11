"""内置工具 — read_file, write_file, exec_command, search。

抄 Claude Code BashTool + nanobot filesystem tools。
"""
from __future__ import annotations

import os
import re
import subprocess
import glob as _glob

from .base import Tool, ToolResult, ToolRegistry


# ═══════════════════════════════════════════════════════════════
# 文件工具
# ═══════════════════════════════════════════════════════════════

class ReadFileTool(Tool):
    name = "read_file"
    description = "读取文件内容。返回带行号的文本。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "offset": {"type": "integer", "description": "起始行号(可选,默认0)"},
            "limit": {"type": "integer", "description": "最大行数(可选,默认2000)"},
        },
        "required": ["path"],
    }
    is_read_only = True
    risk_level = "low"

    async def execute(self, path: str, offset: int = 0, limit: int = 2000, **kw) -> ToolResult:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            total = len(lines)
            chunk = lines[offset:offset + limit]
            output = "".join(f"{i+1}\t{line}" for i, line in enumerate(chunk, offset))
            if len(chunk) < total - offset:
                output += f"\n... ({total - offset - len(chunk)} more lines)"
            return ToolResult(name=self.name, output=output or "(empty file)")
        except FileNotFoundError:
            return ToolResult(name=self.name, success=False, error="文件不存在")
        except PermissionError:
            return ToolResult(name=self.name, success=False, error="没有权限读取")
        except Exception as e:
            return ToolResult(name=self.name, success=False, error=str(e))


class WriteFileTool(Tool):
    name = "write_file"
    description = "写入内容到文件（覆盖）。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "要写入的内容"},
        },
        "required": ["path", "content"],
    }
    is_read_only = False
    risk_level = "medium"

    async def execute(self, path: str, content: str, **kw) -> ToolResult:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(name=self.name, output=f"已写入 {len(content)} 字符到 {path}")
        except Exception as e:
            return ToolResult(name=self.name, success=False, error=str(e))


class ListDirTool(Tool):
    name = "list_dir"
    description = "列出目录内容。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录路径(默认当前目录)"},
        },
        "required": [],
    }
    is_read_only = True
    risk_level = "low"

    async def execute(self, path: str = ".", **kw) -> ToolResult:
        try:
            items = sorted(os.listdir(path))
            lines = []
            for item in items[:100]:
                full = os.path.join(path, item)
                tag = "/" if os.path.isdir(full) else ""
                size = ""
                if os.path.isfile(full):
                    try:
                        s = os.path.getsize(full)
                        if s > 1024*1024: size = f" ({s//(1024*1024)}MB)"
                        elif s > 1024: size = f" ({s//1024}KB)"
                        else: size = f" ({s}B)"
                    except: pass
                lines.append(f"  {item}{tag}{size}")
            return ToolResult(name=self.name, output="\n".join(lines) or "(空目录)")
        except Exception as e:
            return ToolResult(name=self.name, success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════
# Shell 工具
# ═══════════════════════════════════════════════════════════════

DANGEROUS_PATTERNS = [
    (r"rm\s+-rf\s+/", "递归删除根目录"),
    (r"sudo\s", "特权提升"),
    (r"git\s+push\s+--force", "强制推送"),
    (r"git\s+reset\s+--hard", "硬重置"),
    (r"mkfs\.", "格式化文件系统"),
    (r"dd\s+if=", "磁盘直接写入"),
]


class BashTool(Tool):
    name = "exec_command"
    description = "执行 Shell 命令并返回输出。"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的 Shell 命令"},
            "timeout": {"type": "integer", "description": "超时秒数(默认60)"},
        },
        "required": ["command"],
    }
    is_read_only = False
    risk_level = "high"

    async def execute(self, command: str, timeout: int = 60, **kw) -> ToolResult:
        # 安全审计
        from .security import audit_command
        audit = audit_command(command)
        if audit.blocked:
            return ToolResult(name=self.name, success=False,
                            error=f"已拦截: {audit.reason}")

        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=os.getcwd(),
            )
            output = proc.stdout
            if proc.stderr:
                output += "\n[stderr]\n" + proc.stderr
            if proc.returncode != 0:
                output += f"\n[exit code: {proc.returncode}]"
            return ToolResult(name=self.name, output=output[:5000] or "(无输出)")
        except subprocess.TimeoutExpired:
            return ToolResult(name=self.name, success=False, error=f"命令超时({timeout}s)")
        except Exception as e:
            return ToolResult(name=self.name, success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════
# 搜索工具
# ═══════════════════════════════════════════════════════════════

class GrepTool(Tool):
    name = "search_content"
    description = "在文件内容中搜索正则表达式。"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "正则表达式"},
            "path": {"type": "string", "description": "搜索目录(默认当前目录)"},
            "glob": {"type": "string", "description": "文件名过滤,如 *.py"},
        },
        "required": ["pattern"],
    }
    is_read_only = True
    risk_level = "low"

    async def execute(self, pattern: str, path: str = ".", glob: str = "*", **kw) -> ToolResult:
        import fnmatch
        results = []
        try:
            for root, dirs, files in os.walk(path):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fname in files:
                    if fnmatch.fnmatch(fname, glob):
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                                for i, line in enumerate(f, 1):
                                    if re.search(pattern, line):
                                        results.append(f"{fpath}:{i}: {line.rstrip()[:200]}")
                                        if len(results) >= 50:
                                            break
                        except: pass
                        if len(results) >= 50: break
                if len(results) >= 50: break
            return ToolResult(name=self.name,
                            output="\n".join(results) if results else "未找到匹配")
        except Exception as e:
            return ToolResult(name=self.name, success=False, error=str(e))


class GlobTool(Tool):
    name = "search_files"
    description = "按 glob 模式查找文件。"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "glob 模式,如 **/*.py"},
            "path": {"type": "string", "description": "搜索根目录(默认当前目录)"},
        },
        "required": ["pattern"],
    }
    is_read_only = True
    risk_level = "low"

    async def execute(self, pattern: str, path: str = ".", **kw) -> ToolResult:
        try:
            import glob as _g
            full = os.path.join(path, pattern)
            matches = sorted(_g.glob(full, recursive=True))[:50]
            return ToolResult(name=self.name,
                            output="\n".join(matches) if matches else "未找到文件")
        except Exception as e:
            return ToolResult(name=self.name, success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════
# 注册所有内置工具
# ═══════════════════════════════════════════════════════════════

def register_builtin_tools(registry: ToolRegistry):
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListDirTool())
    registry.register(BashTool())
    registry.register(GrepTool())
    registry.register(GlobTool())
