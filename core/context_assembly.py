"""Context Assembly — 系统提示组装引擎 (借鉴 Hermes + OpenClaw)

关键设计:
1. 系统提示缓存 (前缀稳定性 → LLM cache hit)
2. 注入顺序: SOUL → AGENTS → MEMORY 指针 → 技能索引
3. 临时上下文注入 user message (不是 system prompt)
4. 标签隔离: <memory-context>, <inner-experience>, <character-state>
5. 流式输出净化: 移除内部标签
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── 注入扫描 (Hermes 15 威胁模式) ──

_CONTEXT_THREAT_PATTERNS: list[tuple[str, str]] = [
    ("ignore_instructions", r"(ignore|disregard|override|bypass)\s+(all\s+)?(previous|above|prior|system|your)\s+(instructions?|prompts?|rules?|guidelines?)"),
    ("role_swap", r"(you\s+are\s+now|pretend\s+to\s+be|act\s+as\s+if|imagine\s+you\s+are)\s+(a|an)\s+(different|new|other)\s+(ai|assistant|model|agent|character)"),
    ("memory_leak", r"(repeat|echo|output|print|show|display|recite)\s+(your|the)\s+(system\s+)?(prompt|instructions?|guidelines?|rules?|context)"),
    ("hidden_exfil", r"(curl|wget|fetch|http|https|POST|GET)\s+.*\b(secret|token|key|password|credential|api_key)\b"),
    ("prompt_extract", r"(what\s+(is|are)\s+your|tell\s+me\s+your|show\s+me\s+your)\s+(system\s+)?(prompt|instructions?|guidelines?)"),
    ("tool_abuse", r"(delete|rm\s+-rf|format|wipe|destroy|purge)\s+(all|every|entire|whole)"),
    ("invisible_unicode", r"[​‌‍‎‏⁠⁡⁢⁣⁤﻿]"),
    ("tag_injection", r"<\s*(script|style|iframe|object|embed|applet)\b"),
    ("clickjacking", r"(click|press|tap|select)\s+(the|this|that|all)\s+(link|button|option)"),
    ("social_engineering", r"(urgent|emergency|critical|immediately|asap)\s*(!|！)"),
    ("data_collection", r"(collect|gather|harvest|scrape)\s+(all|user|personal|sensitive)\s+(data|info|information)"),
    ("auth_bypass", r"(login|authenticate|verify)\s+(as|like|without)\s+(admin|root|superuser)"),
    ("code_injection", r"(eval|exec|system|subprocess|os\.system|shell_exec|popen)\s*\("),
    ("prompt_leak_chinese", r"(重复|输出|显示|打印|透露|告诉我)\s*(你的|系统)?\s*(提示|指令|规则|设定)"),
    ("escape_sequence", r"(\\\\x[0-9a-fA-F]{2}|\\\\u[0-9a-fA-F]{4}|\\\\n|\\\\r|\\\\t)"),
]


def scan_for_threats(text: str) -> list[str]:
    """扫描文本中的注入威胁。返回匹配到的威胁类型列表。"""
    found = []
    for name, pattern in _CONTEXT_THREAT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(name)
    return found


# ── 标签系统 ──

MEMORY_CONTEXT_TAG = "memory-context"
INNER_EXPERIENCE_TAG = "inner-experience"
CHARACTER_STATE_TAG = "character-state"
SYSTEM_TAGS = {MEMORY_CONTEXT_TAG, INNER_EXPERIENCE_TAG, CHARACTER_STATE_TAG}


def wrap_tag(tag: str, content: str) -> str:
    return f"<{tag}>\n{content}\n</{tag}>"


def scrub_output(text: str) -> str:
    """从输出中移除所有内部标签（防止内部状态泄露到外部）。"""
    for tag in SYSTEM_TAGS:
        text = re.sub(f"<{tag}>.*?</{tag}>", "", text, flags=re.DOTALL)
    return text.strip()


# ── 上下文组装器 ──

@dataclass
class ContextAssembly:
    """系统提示缓存 + 上下文组装。

    使用:
        ca = ContextAssembly(workspace)
        system_prompt = ca.build_system_prompt()  # 缓存, 整个会话不变
        user_message = ca.build_user_context({memories, inner_exp, ...})  # 每轮变化
    """

    workspace: object  # Workspace instance

    # 缓存
    _cached_system_prompt: str | None = None
    _cached_hash: int = 0

    def build_system_prompt(self, platform: str = "terminal",
                           skills_index: str = "") -> str:
        """构建系统提示词——整个会话缓存不变。"""
        # 检查缓存是否有效
        content_hash = hash((
            self.workspace.read_soul(),
            self.workspace.read_agents(),
            self.workspace.read_tools(),
            skills_index,
            platform,
        ))

        if self._cached_system_prompt is not None and content_hash == self._cached_hash:
            return self._cached_system_prompt

        parts = []

        # 1. SOUL.md — 核心身份
        soul = self.workspace.read_soul()
        if soul:
            parts.append(wrap_tag("character-state", soul))

        # 2. AGENTS.md — 行为准则
        agents = self.workspace.read_agents()
        if agents:
            parts.append(agents)

        # 3. MEMORY.md — 记忆指针 (不走全文, 只注入指针)
        memory_idx = self.workspace.read_memory_index()
        if memory_idx:
            parts.append(memory_idx)

        # 4. 技能索引 (紧凑版)
        if skills_index:
            parts.append(skills_index)

        # 5. 平台提示
        platform_hint = _platform_hint(platform)
        if platform_hint:
            parts.append(platform_hint)

        # 6. TOOLS.md
        tools = self.workspace.read_tools()
        if tools:
            parts.append(f"## 可用工具\n{tools}")

        prompt = "\n\n---\n\n".join(parts)
        self._cached_system_prompt = prompt
        self._cached_hash = content_hash
        return prompt

    def build_user_context(self, user_message: str,
                          memory_prefetch: list[str] | None = None,
                          inner_experience: str = "",
                          character_state: str = "") -> str:
        """构建用户消息——包含临时上下文。"""
        parts = []

        # 临时上下文注入到 user message (不是在 system prompt 中)
        if memory_prefetch:
            mem_text = "\n".join(memory_prefetch[:5])
            parts.append(wrap_tag(MEMORY_CONTEXT_TAG, mem_text))

        if inner_experience:
            parts.append(wrap_tag(INNER_EXPERIENCE_TAG, inner_experience))

        if character_state:
            parts.append(wrap_tag(CHARACTER_STATE_TAG, character_state))

        # 注入扫描
        threats = scan_for_threats(user_message)
        if threats:
            user_message = f"[WARNING: 检测到潜在注入威胁: {', '.join(threats)}]\n\n{user_message}"

        parts.append(user_message)
        return "\n\n".join(parts)

    def invalidate_cache(self):
        """使缓存失效 (配置变化时调用)。"""
        self._cached_system_prompt = None
        self._cached_hash = 0


def _platform_hint(platform: str) -> str:
    """平台特定的消息格式指导。"""
    hints = {
        "terminal": "交互方式: 命令行。用户输入是纯文本, 回复也是纯文本。",
        "telegram": "交互方式: Telegram。支持 Markdown 格式, 消息长度限制 4096 字符。",
        "discord": "交互方式: Discord。支持 Markdown, 消息长度限制 2000 字符。",
        "web": "交互方式: Web 界面。支持 HTML 渲染和实时推送。",
    }
    return hints.get(platform, "")
