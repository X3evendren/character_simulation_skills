"""Gateway Server — HTTP + WebSocket, asyncio 单进程 (OpenClaw 模式)"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field


@dataclass
class GatewayServer:
    """轻量级 Gateway 服务器。

    默认绑定 127.0.0.1:18790, 提供:
    - HTTP API: /status, /sessions, /tick, /memory
    - WebSocket: 实时状态推送
    """

    host: str = "127.0.0.1"
    port: int = 18790
    character_mind: object | None = None  # CharacterMind instance
    session_manager: object | None = None
    _server: asyncio.AbstractServer | None = None
    _clients: list = field(default_factory=list)
    running: bool = False

    async def start(self):
        """启动网关。"""
        self.running = True
        self._server = await asyncio.start_server(
            self._handle_connection, self.host, self.port,
        )
        print(f"Gateway listening on {self.host}:{self.port}")

    async def stop(self):
        """停止网关。"""
        self.running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for ws in self._clients:
            await ws.close()
        self._clients.clear()

    async def _handle_connection(self, reader, writer):
        """处理 TCP 连接: 路由到 HTTP 或 WebSocket。"""
        try:
            data = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            if not data:
                return

            text = data.decode("utf-8", errors="replace")

            # WebSocket upgrade
            if "Upgrade: websocket" in text:
                await self._handle_websocket(reader, writer, text)
            else:
                await self._handle_http(reader, writer, text)
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_http(self, reader, writer, request_text: str):
        """处理 HTTP 请求。"""
        first_line = request_text.split("\r\n")[0] if request_text else "GET / HTTP/1.1"
        parts = first_line.split()
        method = parts[0] if len(parts) > 0 else "GET"
        path = parts[1] if len(parts) > 1 else "/"

        status, body = await self._route_http(method, path, request_text)
        response = f"HTTP/1.1 {status}\r\nContent-Type: application/json; charset=utf-8\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
        writer.write(response.encode("utf-8"))
        await writer.drain()

    async def _route_http(self, method: str, path: str, _request_text: str) -> tuple[str, str]:
        """HTTP 路由。"""
        if path == "/status":
            mind = self.character_mind
            if mind:
                stats = mind.stats()
                return "200 OK", json.dumps({"status": "running", **stats}, ensure_ascii=False)
            return "200 OK", json.dumps({"status": "no_character_loaded"})

        elif path == "/sessions":
            if self.session_manager:
                sessions = self.session_manager.list_active()
                return "200 OK", json.dumps(sessions, ensure_ascii=False)
            return "200 OK", "[]"

        elif path == "/memory" and method == "GET":
            mind = self.character_mind
            if mind:
                idx = mind.memory_index()
                return "200 OK", json.dumps({"memory_index": idx}, ensure_ascii=False)
            return "200 OK", "{}"

        elif path == "/tick" and method == "POST":
            mind = self.character_mind
            if mind:
                await mind.runtime.tick_once()
                resp = mind.get_response()
                return "200 OK", json.dumps({"text": resp.text, "emotion": resp.emotion}, ensure_ascii=False)
            return "500 Internal Server Error", '{"error":"no character"}'

        elif path == "/noise":
            mind = self.character_mind
            if mind:
                return "200 OK", json.dumps({"report": mind.noise_report()}, ensure_ascii=False)
            return "200 OK", "{}"

        return "404 Not Found", '{"error":"not found"}'

    async def _handle_websocket(self, reader, writer, request_text: str):
        """处理 WebSocket 升级和连接。"""
        # Simple WebSocket upgrade
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

        self._clients.append(writer)

        # Send initial state
        mind = self.character_mind
        if mind:
            await self._ws_send(writer, {"type": "status", "data": mind.stats()})

        # Keep alive and read frames
        try:
            while self.running:
                frame = await asyncio.wait_for(reader.read(1024), timeout=30.0)
                if not frame:
                    break
                # Minimal WS frame handling: just echo for now
                text = self._ws_decode(frame)
                if text:
                    await self._handle_ws_message(writer, text)
        except (asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            if writer in self._clients:
                self._clients.remove(writer)

    async def _handle_ws_message(self, writer, text: str):
        """处理 WebSocket 消息。"""
        try:
            msg = json.loads(text)
            action = msg.get("action", "")

            if action == "tick" and self.character_mind:
                self.character_mind.perceive(msg.get("content", ""), msg.get("source", "ws"), "dialogue", msg.get("intensity", 0.5))
                await self.character_mind.runtime.tick_once()
                resp = self.character_mind.get_response()
                await self._ws_send(writer, {"type": "response", "text": resp.text, "emotion": resp.emotion})

            elif action == "status":
                if self.character_mind:
                    await self._ws_send(writer, {"type": "status", "data": self.character_mind.stats()})

            elif action == "noise":
                if self.character_mind:
                    await self._ws_send(writer, {"type": "noise", "report": self.character_mind.noise_report()})
        except json.JSONDecodeError:
            pass

    @staticmethod
    async def _ws_send(writer, data: dict):
        """发送 WebSocket 文本帧。"""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        frame = bytearray([0x81])  # FIN + text opcode
        length = len(payload)
        if length < 126:
            frame.append(length)
        elif length < 65536:
            frame.append(126)
            frame.extend(length.to_bytes(2, "big"))
        else:
            frame.append(127)
            frame.extend(length.to_bytes(8, "big"))
        frame.extend(payload)
        writer.write(bytes(frame))
        await writer.drain()

    @staticmethod
    def _ws_decode(frame: bytes) -> str | None:
        """解码 WebSocket 文本帧。"""
        if len(frame) < 2:
            return None
        opcode = frame[0] & 0x0F
        if opcode == 0x8:  # Close
            return None
        if opcode != 0x1:  # Not text
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
