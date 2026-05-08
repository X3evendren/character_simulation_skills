"""Workspace — 文件系统工作区管理 (OpenClaw 模式)

~/.character_mind/workspaces/<name>/
  SOUL.md        — 角色核心身份
  AGENTS.md      — Agent 行为准则/基线规则
  MEMORY.md      — 长期记忆指针索引
  TOOLS.md       — 工具使用说明
  config.json    — 角色配置
"""
from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass, field


@dataclass
class Workspace:
    """角色工作区——管理所有配置和身份文件。"""

    name: str
    base_dir: str = ""

    def __post_init__(self):
        if not self.base_dir:
            home = os.path.expanduser("~")
            self.base_dir = os.path.join(home, ".character_mind", "workspaces", self.name)

    @property
    def path(self) -> str:
        return self.base_dir

    # ═══ 初始化和持久化 ═══

    def init(self, character_profile: dict):
        """从角色配置初始化工作区。"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "skills"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "memory"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "sessions"), exist_ok=True)

        self._write_soul(character_profile)
        self._write_agents(character_profile)
        self._write_tools()
        self._write_config(character_profile)

    def exists(self) -> bool:
        return os.path.exists(os.path.join(self.base_dir, "config.json"))

    # ═══ SOUL.md ═══

    def _write_soul(self, profile: dict):
        p = profile.get("personality", {})
        t = profile.get("trauma", {})
        iw = profile.get("ideal_world", {})

        lines = [f"# {profile.get('name', '角色')} 的灵魂", ""]
        lines.append(f"## 核心身份")
        lines.append(f"OCEAN: O={p.get('openness',0.5):.1f} "
                     f"C={p.get('conscientiousness',0.5):.1f} "
                     f"E={p.get('extraversion',0.5):.1f} "
                     f"A={p.get('agreeableness',0.5):.1f} "
                     f"N={p.get('neuroticism',0.5):.1f}")
        lines.append(f"依恋风格: {p.get('attachment_style','secure')}")
        lines.append("")

        if p.get("defense_style"):
            lines.append(f"防御机制: {', '.join(p['defense_style'])}")
            lines.append("")

        schemas = t.get("active_schemas", [])
        if schemas:
            lines.append("## 核心冲突")
            for s in schemas:
                lines.append(f"- {s}")
            lines.append("")

        triggers = t.get("trauma_triggers", [])
        if triggers:
            lines.append("## 创伤触发")
            for tr in triggers:
                lines.append(f"- {tr}")
            lines.append("")

        if iw.get("ideal_self"):
            lines.append(f"## 理想自我")
            lines.append(f"{iw['ideal_self']}")

        self.write_file("SOUL.md", "\n".join(lines))

    def read_soul(self) -> str:
        return self.read_file("SOUL.md")

    # ═══ AGENTS.md ═══

    def _write_agents(self, profile: dict):
        lines = [f"# {profile.get('name','角色')} 行为准则", ""]
        lines.append("## 核心规则")
        lines.append("1. 行为由此心理画像驱动，不施加外部规范")
        lines.append("2. 回应简短(2-3句)，不解释动机，不分析自己")
        lines.append("3. 潜台词留给情境传达——不把弦外之音翻译成明台词")
        lines.append("4. 呈现角色的本来面目，包括负面、不健康或有缺陷的反应")
        lines.append("")
        lines.append("## 表达策略")
        lines.append("- 内部体验与外部表达可以不一致")
        lines.append("- 沉默、回避、冷处理都是有效的表达方式")
        lines.append("- 用行为传达内心，而不是用语言")
        lines.append("")
        lines.append("## 记忆使用")
        lines.append("- MEMORY.md 中的指针指向角色的核心记忆")
        lines.append("- 不主动回忆，除非情境触发")
        lines.append("- 记忆可以被想起但不主动提及")
        self.write_file("AGENTS.md", "\n".join(lines))

    def read_agents(self) -> str:
        return self.read_file("AGENTS.md")

    # ═══ MEMORY.md ═══

    def write_memory_index(self, content: str):
        """写入记忆指针索引 (纯指针, 不含内容)。"""
        self.write_file("MEMORY.md", content)

    def read_memory_index(self) -> str:
        return self.read_file("MEMORY.md")

    # ═══ TOOLS.md ═══

    def _write_tools(self):
        lines = ["# 工具说明", ""]
        lines.append("## 可用工具")
        lines.append("- cognitive_frame: 深度心理分析 (L0-L3 自动触发)")
        lines.append("- memory_search: 搜索角色记忆")
        lines.append("- memory_timeline: 时间线检索")
        lines.append("- expression_filter: 内部体验→外部表达转换")
        lines.append("")
        lines.append("## 权限")
        lines.append("- 所有工具在角色运行时自动可用")
        lines.append("- 无需手动调用")
        self.write_file("TOOLS.md", "\n".join(lines))

    def read_tools(self) -> str:
        return self.read_file("TOOLS.md")

    # ═══ config.json ═══

    def _write_config(self, profile: dict):
        config = {
            "name": profile.get("name", "角色"),
            "created_at": time.time(),
            "version": "2.0",
            "personality": profile.get("personality", {}),
            "trauma": profile.get("trauma", {}),
            "ideal_world": profile.get("ideal_world", {}),
            "motivation": profile.get("motivation", {}),
            "relations": profile.get("relations", {}),
        }
        with open(os.path.join(self.base_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def read_config(self) -> dict:
        path = os.path.join(self.base_dir, "config.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    # ═══ 工具方法 ═══

    def write_file(self, filename: str, content: str):
        with open(os.path.join(self.base_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    def read_file(self, filename: str) -> str:
        path = os.path.join(self.base_dir, filename)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
        return ""

    def list_skills(self) -> list[str]:
        skills_dir = os.path.join(self.base_dir, "skills")
        if not os.path.exists(skills_dir):
            return []
        return [d for d in os.listdir(skills_dir)
                if os.path.isdir(os.path.join(skills_dir, d))]

    def list_sessions(self) -> list[str]:
        sessions_dir = os.path.join(self.base_dir, "sessions")
        if not os.path.exists(sessions_dir):
            return []
        return sorted([f for f in os.listdir(sessions_dir) if f.endswith(".json")])

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "base_dir": self.base_dir,
            "config": self.read_config(),
            "skill_count": len(self.list_skills()),
            "session_count": len(self.list_sessions()),
        }
