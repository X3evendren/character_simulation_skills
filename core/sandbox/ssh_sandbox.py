"""SSH Sandbox — 远程 SSH 主机上执行工具命令。

通过 subprocess + ssh CLI 实现。可选 asyncssh 依赖。
"""
from __future__ import annotations

import asyncio
import subprocess
import time
import uuid
from dataclasses import dataclass


@dataclass
class SSHSandboxResult:
    """SSH 沙箱执行结果。"""
    success: bool
    output: str
    error: str = ""
    execution_time: float = 0.0
    exit_code: int = -1


class SSHSandboxExecutor:
    """SSH 远程执行器。

    配置: CHARACTER_MIND_SANDBOX=ssh:user@host[:port]
    """

    def __init__(self, host: str, user: str = "",
                 port: int = 22, key_file: str = "",
                 timeout_seconds: float = 30.0):
        self.host = host
        self.user = user
        self.port = port
        self.key_file = key_file
        self.timeout_seconds = timeout_seconds

    @property
    def target(self) -> str:
        if self.user:
            return f"{self.user}@{self.host}"
        return self.host

    async def execute(self, command: str) -> SSHSandboxResult:
        """通过 SSH 执行命令。"""
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={int(self.timeout_seconds)}",
            "-p", str(self.port),
        ]
        if self.key_file:
            ssh_cmd.extend(["-i", self.key_file])
        ssh_cmd.append(self.target)
        ssh_cmd.append(command)

        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout_seconds,
            )
            elapsed = time.time() - start

            output = (stdout or b"").decode("utf-8", errors="replace")
            err_output = (stderr or b"").decode("utf-8", errors="replace")

            return SSHSandboxResult(
                success=proc.returncode == 0,
                output=output.strip() or "(no output)",
                error=err_output.strip() if proc.returncode != 0 else "",
                execution_time=elapsed,
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            return SSHSandboxResult(
                False, "", f"SSH 命令超时 ({self.timeout_seconds}s)",
                execution_time=time.time() - start,
            )
        except Exception as e:
            return SSHSandboxResult(
                False, "", str(e),
                execution_time=time.time() - start,
            )

    @classmethod
    def from_env(cls) -> "SSHSandboxExecutor | None":
        """从环境变量解析 SSH 沙箱配置。"""
        import os
        sandbox = os.environ.get("CHARACTER_MIND_SANDBOX", "")
        if not sandbox.startswith("ssh:"):
            return None
        target = sandbox[4:]  # 去掉 "ssh:"
        user_host = target.split("@")
        if len(user_host) == 2:
            user = user_host[0]
            host_port = user_host[1].split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 22
            return cls(host=host, user=user, port=port)
        return cls(host=target)

    @classmethod
    def check_available(cls, host: str = "localhost") -> bool:
        """检查 SSH 连接是否可用。"""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", host, "echo ok"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False
