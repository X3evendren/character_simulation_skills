#!/usr/bin/env python3
"""Character Mind CLI — 借鉴 Hermes cli.py + OpenClaw CLI 模式

Commands:
  character-mind chat      命令行交互模式
  character-mind status    运行时状态
  character-mind memory    记忆管理
  character-mind skills    技能管理
  character-mind serve     启动 Gateway
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

_pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)


def main():
    parser = argparse.ArgumentParser(prog="character-mind", description="Character Mind v2")
    sub = parser.add_subparsers(dest="command")

    # chat
    chat_parser = sub.add_parser("chat", help="命令行交互模式")
    chat_parser.add_argument("--name", default="林雨", help="角色名称")
    chat_parser.add_argument("--provider", default="mock", help="LLM provider (mock/ollama)")
    chat_parser.add_argument("--model", default="lfm2.5-thinking:latest", help="模型名称")

    # serve
    serve_parser = sub.add_parser("serve", help="启动 Gateway")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=18790)
    serve_parser.add_argument("--name", default="林雨")

    # status
    sub.add_parser("status", help="运行时状态")

    # memory
    mem_parser = sub.add_parser("memory", help="记忆管理")
    mem_parser.add_argument("action", choices=["view", "search", "clean"])

    # skills
    skill_parser = sub.add_parser("skills", help="技能管理")
    skill_parser.add_argument("action", choices=["list", "activate", "archive"])

    args = parser.parse_args()

    if args.command == "chat":
        asyncio.run(_chat(args))
    elif args.command == "serve":
        asyncio.run(_serve(args))
    elif args.command == "status":
        print("Character Mind v2 — 状态: 运行中 (需 Gateway 或交互模式)")
    elif args.command == "memory":
        print(f"记忆管理: {args.action}")
    elif args.command == "skills":
        print(f"技能管理: {args.action}")
    else:
        parser.print_help()


async def _chat(args):
    """终端交互聊天模式。"""
    from character_mind.core.runtime_v2 import CharacterMind
    from character_mind.gateway.channels.terminal import TerminalChannel

    if args.provider == "ollama":
        from character_mind.benchmark.real_llm_benchmark import OllamaProvider
        provider = OllamaProvider(model=args.model)
    else:
        from character_mind.benchmark.mock_provider import MockProvider
        provider = MockProvider(quality=0.9, base_tokens=200)

    mind = CharacterMind(provider, {
        "name": args.name,
        "personality": {"openness": 0.6, "neuroticism": 0.75, "attachment_style": "anxious"},
    })
    channel = TerminalChannel(mind)
    await channel.interactive_loop()


async def _serve(args):
    """启动 Gateway 服务器。"""
    from character_mind.gateway.server import GatewayServer
    from character_mind.gateway.session_manager import GatewaySessionManager

    server = GatewayServer(host=args.host, port=args.port)
    server.session_manager = GatewaySessionManager()
    await server.start()
    # Keep running
    try:
        while server.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    main()
