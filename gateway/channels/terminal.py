"""Terminal Channel — 标准输入/输出交互 (内置默认通道)"""
from __future__ import annotations

import asyncio
import json
from .base import ChannelAdapter


class TerminalChannel(ChannelAdapter):
    """命令行交互通道。

    stdin → CharacterMind → stdout
    """

    def __init__(self, character_mind=None):
        self.mind = character_mind
        self.running = False

    async def connect(self):
        self.running = True

    async def on_message(self, text: str, sender_id: str = "") -> dict:
        """用户输入 → Cognitive Frame → 回应。"""
        if self.mind is None:
            return {"error": "no character loaded"}
        self.mind.perceive(text, sender_id or "terminal", "dialogue")
        await self.mind.runtime.tick_once()
        resp = self.mind.get_response()
        return {"text": resp.text, "emotion": resp.emotion, "action": resp.action}

    async def send_message(self, text: str, target_id: str = ""):
        """输出到终端。"""
        print(f"\n[{self.mind.character_profile.get('name', '角色')}]: {text}")

    async def disconnect(self):
        self.running = False

    async def interactive_loop(self):
        """交互式终端循环。"""
        name = self.mind.character_profile.get("name", "角色") if self.mind else "角色"
        print(f"Character Mind v2 — {name}")
        print("输入消息开始对话, /quit 退出, /status 状态, /noise 噪音\n")

        await self.connect()
        try:
            while self.running:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("> "))
                except (EOFError, KeyboardInterrupt):
                    break

                if not user_input.strip():
                    continue
                if user_input == "/quit":
                    break
                if user_input == "/status" and self.mind:
                    print(json.dumps(self.mind.stats(), ensure_ascii=False, indent=2))
                    continue
                if user_input == "/noise" and self.mind:
                    print(self.mind.noise_report())
                    continue

                response = await self.on_message(user_input)
                if response.get("text"):
                    await self.send_message(response["text"])
        finally:
            await self.disconnect()
            print("\n再见。")
