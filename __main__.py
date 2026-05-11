"""Character Mind v3 — 命令行入口。

用法:
  cd character_mind_v3
  python -m cli chat --provider openai --api-key sk-xxx
  python -m cli chat --provider openai --base-url http://localhost:11434/v1 --psych-model qwen2.5:7b --gen-model qwen2.5:14b
  python -m cli serve --port 18790
"""
from cli.main import main

if __name__ == "__main__":
    main()
