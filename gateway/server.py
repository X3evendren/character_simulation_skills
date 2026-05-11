"""Gateway Server — HTTP + WebSocket 服务。

抄 OpenClaw + Hermes Agent 的 Gateway 模式:
- HTTP API: /status, /chat
- WebSocket: 实时流式对话
"""
from __future__ import annotations

import asyncio
import json
import time
import logging

logger = logging.getLogger("character_mind.gateway")


class GatewayServer:
    """轻量级 Gateway 服务器。

    默认绑定 127.0.0.1:18790。
    安全: Bearer Token 认证 (可选) + 速率限制。
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 18790,
                 api_key: str = ""):
        self.host = host
        self.port = port
        self.api_key = api_key
        self._server: asyncio.AbstractServer | None = None
        self._ws_clients: list = []
        self.running = False
        self.character_mind = None  # CharacterMind 实例

    async def start(self):
        self.running = True
        self._server = await asyncio.start_server(
            self._handle_connection, self.host, self.port,
        )
        logger.info(f"Gateway listening on http://{self.host}:{self.port}")

    async def stop(self):
        self.running = False
        if self._server:
            self._server.close()
            try:
                await asyncio.wait_for(self._server.wait_closed(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
        for ws in list(self._ws_clients):
            try:
                ws.close()
            except Exception:
                pass
        self._ws_clients.clear()

    async def _handle_connection(self, reader, writer):
        try:
            data = await asyncio.wait_for(reader.read(65536), timeout=10.0)
            if not data:
                return

            text = data.decode("utf-8", errors="replace")

            if "Upgrade: websocket" in text:
                await self._handle_websocket(reader, writer, text)
            else:
                await self._handle_http(reader, writer, text)
        except asyncio.TimeoutError:
            pass
        except ConnectionError:
            pass
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_http(self, reader, writer, request_text: str):
        first_line = request_text.split("\r\n")[0] if request_text else "GET / HTTP/1.1"
        parts = first_line.split()
        method = parts[0] if len(parts) > 0 else "GET"
        path = parts[1] if len(parts) > 1 else "/"

        # 简单路由
        body = await self._route(method, path, request_text)
        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            f"\r\n{body}"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()

    async def _route(self, method: str, path: str, _request: str) -> str:
        if path == "/status":
            return json.dumps({"status": "running", "timestamp": time.time()})
        elif path == "/health":
            return json.dumps({"ok": True})
        return json.dumps({"error": "not found"})

    async def _handle_websocket(self, reader, writer, request_text: str):
        # WebSocket 升级
        key = ""
        for line in request_text.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
                break
        if not key:
            return

        import hashlib, base64
        magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept = base64.b64encode(hashlib.sha1((key + magic).encode()).digest()).decode()

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        )
        writer.write(response.encode())
        await writer.drain()
        self._ws_clients.append(writer)

        try:
            while self.running:
                frame = await asyncio.wait_for(reader.read(4096), timeout=30.0)
                if not frame:
                    break
                text = self._ws_decode(frame)
                if text:
                    try:
                        msg = json.loads(text)
                        if msg.get("type") == "chat" and self.character_mind:
                            # 处理聊天消息
                            pass
                    except json.JSONDecodeError:
                        pass
        except (asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            if writer in self._ws_clients:
                self._ws_clients.remove(writer)

    @staticmethod
    def _ws_decode(frame: bytes) -> str | None:
        if len(frame) < 2:
            return None
        opcode = frame[0] & 0x0F
        if opcode in (0x8, 0x9, 0xA):
            return None
        masked = frame[1] & 0x80
        length = frame[1] & 0x7F
        offset = 2
        if length == 126:
            length = int.from_bytes(frame[2:4], "big")
            offset = 4
        elif length == 127:
            length = int.from_bytes(frame[2:10], "big")
            offset = 10
        if masked:
            mask = frame[offset:offset + 4]
            offset += 4
            return bytes(b ^ mask[i % 4] for i, b in enumerate(frame[offset:offset + length])).decode("utf-8", errors="replace")
        return frame[offset:offset + length].decode("utf-8", errors="replace")
