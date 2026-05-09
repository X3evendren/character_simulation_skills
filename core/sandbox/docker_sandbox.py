"""Docker Sandbox — Docker 容器内执行工具命令。

使用 subprocess + docker CLI 实现。Docker 不可用时优雅回退。
"""
from __future__ import annotations

import asyncio
import os
import shutil
import time
import uuid
from dataclasses import dataclass


@dataclass
class DockerSandboxResult:
    """Docker 沙箱执行结果。"""
    success: bool
    output: str
    error: str = ""
    execution_time: float = 0.0
    exit_code: int = -1


class DockerSandboxExecutor:
    """Docker 容器内执行命令。

    用法:
        executor = DockerSandboxExecutor(image="ubuntu:latest")
        result = await executor.execute("echo hello")
    """

    def __init__(self, image: str = "ubuntu:latest",
                 memory_limit: str = "256m",
                 cpu_limit: float = 0.5,
                 network_enabled: bool = False,
                 timeout_seconds: float = 30.0):
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.network_enabled = network_enabled
        self.timeout_seconds = timeout_seconds
        self._available = shutil.which("docker") is not None

    @property
    def available(self) -> bool:
        return self._available

    async def execute(self, command: str,
                      work_dir: str = "/workspace") -> DockerSandboxResult:
        """在 Docker 容器中执行命令。"""
        if not self._available:
            return DockerSandboxResult(
                False, "", "Docker 不可用——请安装 Docker 或使用本地执行器"
            )

        container_name = f"cm_sandbox_{uuid.uuid4().hex[:8]}"
        network_flag = "" if self.network_enabled else "--network none"

        docker_cmd = (
            f"docker run --rm --name {container_name} "
            f"--memory={self.memory_limit} --cpus={self.cpu_limit} "
            f"{network_flag} "
            f"-w {work_dir} "
            f"{self.image} "
            f"/bin/sh -c {_shell_escape(command)}"
        )

        start = time.time()
        try:
            proc = await asyncio.create_subprocess_shell(
                docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout_seconds,
            )
            elapsed = time.time() - start

            output = (stdout or b"").decode("utf-8", errors="replace")
            err_output = (stderr or b"").decode("utf-8", errors="replace")

            return DockerSandboxResult(
                success=proc.returncode == 0,
                output=output.strip() or "(no output)",
                error=err_output.strip() if proc.returncode != 0 else "",
                execution_time=elapsed,
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            # 清理可能的残留容器
            await self._cleanup_container(container_name)
            return DockerSandboxResult(
                False, "", f"Docker 命令超时 ({self.timeout_seconds}s)",
                execution_time=time.time() - start,
            )
        except Exception as e:
            return DockerSandboxResult(
                False, "", str(e),
                execution_time=time.time() - start,
            )

    async def _cleanup_container(self, name: str) -> None:
        """清理残留容器。"""
        try:
            proc = await asyncio.create_subprocess_shell(
                f"docker rm -f {name} 2>/dev/null",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
        except Exception:
            pass

    @classmethod
    def check_available(cls) -> bool:
        """检查 Docker 是否可用。"""
        return shutil.which("docker") is not None


def _shell_escape(cmd: str) -> str:
    """简单的 shell 转义——将命令用单引号包裹。"""
    escaped = cmd.replace("'", "'\\''")
    return f"'{escaped}'"
