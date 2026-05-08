"""Gateway — Character Mind 网关。

轻量化, 借鉴 OpenClaw Gateway 模式但保持 Python 简洁。
单进程 asyncio, HTTP + WebSocket, 会话管理, 通道适配。
"""
from .server import GatewayServer
from .session_manager import GatewaySessionManager
from .channels.base import ChannelAdapter
from .channels.terminal import TerminalChannel
