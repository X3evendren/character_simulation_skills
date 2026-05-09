"""Security Sandbox — 工具执行安全隔离。

支持 Docker 容器和 SSH 远程执行后端。
非 OWNER 会话强制沙箱——可配置回退策略。
"""
from .docker_sandbox import DockerSandboxExecutor
from .ssh_sandbox import SSHSandboxExecutor
