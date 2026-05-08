"""Channel Adapter ABC — 借鉴 OpenClaw 的 Channel Plugin 模式"""
from abc import ABC, abstractmethod


class ChannelAdapter(ABC):
    """平台适配器抽象基类。

    每个平台实现: connect(), on_message(), send_message().
    """

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def on_message(self, text: str, sender_id: str = "") -> dict: ...

    @abstractmethod
    async def send_message(self, text: str, target_id: str = "") -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...
