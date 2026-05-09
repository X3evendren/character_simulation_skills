"""Prepared Runtime Facts — 启动时一次性编码运行时信息。

消除热路径上的重复 os.environ 查询、提供者检测和模型解析。
每个 Fact 是 frozen dataclass，在 CharacterMind.__init__() 时构造一次后不可变。
"""
from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass, field


# ── Fact 类型 ──


@dataclass(frozen=True)
class ProviderFact:
    """LLM 提供者运行时信息。"""
    name: str                       # "openai" / "deepseek" / "ollama" / "mock"
    base_url: str = ""              # API 端点
    model: str = ""                 # 当前模型名称
    supports_thinking: bool = False # 是否支持 reasoning/thinking 模式
    supports_cache: bool = False    # 是否支持 prompt caching
    max_context: int = 128000       # 最大上下文窗口


@dataclass(frozen=True)
class ModelFact:
    """模型能力运行时信息。"""
    model_id: str
    provider_name: str
    is_local: bool = False          # 本地模型 (ollama 等)
    supports_json_mode: bool = True
    supports_tools: bool = True
    default_temperature: float = 0.3
    default_max_tokens: int = 4096


@dataclass(frozen=True)
class ChannelFact:
    """通道/平台运行时信息。"""
    name: str                       # "terminal" / "gateway" / "telegram" 等
    is_interactive: bool = False    # 是否需要交互式输入
    trust_level: str = "guest"      # 默认信任级别
    supports_markdown: bool = False


@dataclass(frozen=True)
class EnvironmentFact:
    """运行环境信息。"""
    platform: str                   # "windows" / "linux" / "darwin"
    python_version: str             # "3.12.4"
    home_dir: str                   # CHARACTER_MIND_HOME 或 ~/.character_mind
    is_container: bool = False      # 是否在 Docker/容器内
    has_docker: bool = False        # Docker 是否可用
    cpu_count: int = 4              # 逻辑 CPU 数


@dataclass(frozen=True)
class RuntimeFacts:
    """聚合所有运行时事实。"""
    provider: ProviderFact
    model: ModelFact
    environment: EnvironmentFact
    channel: ChannelFact = field(default_factory=lambda: ChannelFact(name="terminal"))
    created_at: float = 0.0         # 构造时间戳
    instance_id: str = ""           # 本次运行实例 ID


# ── 工厂函数 ──


def detect_provider(provider_arg=None, model_arg: str = "") -> ProviderFact:
    """从参数或环境变量检测 LLM 提供者。"""
    if provider_arg is not None:
        return _provider_from_obj(provider_arg, model_arg)

    pname = os.environ.get("CHARACTER_MIND_PROVIDER", "mock").lower()
    return _provider_from_name(pname, model_arg)


def _provider_from_obj(obj, model: str) -> ProviderFact:
    """从现有 provider 对象推断 ProviderFact。"""
    name = getattr(obj, "__class__", type(obj)).__name__.lower()
    base_url = ""
    supports_thinking = False
    supports_cache = False

    if hasattr(obj, "base_url"):
        base_url = str(obj.base_url)
    if "deepseek" in name:
        supports_thinking = True
    if "anthropic" in name or "claude" in name:
        supports_cache = True
        supports_thinking = True

    return ProviderFact(
        name=name,
        base_url=base_url,
        model=model or getattr(obj, "model", ""),
        supports_thinking=supports_thinking,
        supports_cache=supports_cache,
    )


def _provider_from_name(name: str, model: str) -> ProviderFact:
    """从名称字符串推断 ProviderFact。"""
    name = name.lower()
    base_urls = {
        "deepseek": "https://api.deepseek.com/v1",
        "openai": "https://api.openai.com/v1",
        "ollama": "http://localhost:11434/v1",
    }
    return ProviderFact(
        name=name,
        base_url=base_urls.get(name, ""),
        model=model or "",
        supports_thinking=name in ("deepseek",),
        supports_cache=name in ("anthropic", "claude"),
    )


def detect_environment(home_override: str = "") -> EnvironmentFact:
    """检测当前运行环境。"""
    home = home_override or os.environ.get(
        "CHARACTER_MIND_HOME",
        os.path.join(os.path.expanduser("~"), ".character_mind"),
    )
    is_linux = sys.platform.startswith("linux")
    has_docker = False
    is_container = os.path.exists("/.dockerenv") if not sys.platform.startswith("win") else False

    if is_linux:
        has_docker = _check_docker_available()

    return EnvironmentFact(
        platform=_platform_name(),
        python_version=platform.python_version(),
        home_dir=home,
        is_container=is_container,
        has_docker=has_docker,
        cpu_count=os.cpu_count() or 4,
    )


def detect_model(model_arg: str = "", provider_fact: ProviderFact | None = None) -> ModelFact:
    """检测模型能力。"""
    model_id = model_arg or os.environ.get("CHARACTER_MIND_MODEL", "")
    provider_name = provider_fact.name if provider_fact else "unknown"
    is_local = provider_name in ("ollama", "lmstudio") if provider_fact else False

    return ModelFact(
        model_id=model_id,
        provider_name=provider_name,
        is_local=is_local,
    )


def build_runtime_facts(
    provider=None,
    model: str = "",
    home: str = "",
    channel_name: str = "terminal",
) -> RuntimeFacts:
    """一站式构造所有 RuntimeFacts。"""
    import time
    import uuid

    pfact = detect_provider(provider, model)
    return RuntimeFacts(
        provider=pfact,
        model=detect_model(model, pfact),
        environment=detect_environment(home),
        channel=ChannelFact(name=channel_name, is_interactive=(channel_name == "terminal")),
        created_at=time.time(),
        instance_id=uuid.uuid4().hex[:12],
    )


# ── 内部辅助 ──


def _platform_name() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("darwin"):
        return "darwin"
    return sys.platform


def _check_docker_available() -> bool:
    import shutil
    return shutil.which("docker") is not None
