"""Scenario Generator — 动态场景生成。

使用 Latin Hypercube Sampling (LHS) 对参数空间进行采样，
生成覆盖 OCEAN、依恋风格、ACE 分数、事件类型组合的测试场景。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


# ── 参数空间定义 ──

PARAMETER_SPACE: dict[str, list] = {
    "openness": [0.2, 0.4, 0.6, 0.8],
    "conscientiousness": [0.2, 0.4, 0.6, 0.8],
    "extraversion": [0.2, 0.4, 0.6, 0.8],
    "agreeableness": [0.2, 0.4, 0.6, 0.8],
    "neuroticism": [0.2, 0.4, 0.6, 0.8],
    "attachment_style": ["secure", "anxious", "avoidant", "fearful_avoidant"],
    "ace_score": [0, 1, 2, 3, 5, 7],
    "event_type": [
        "social", "romantic", "conflict", "trauma",
        "moral_choice", "routine", "betrayal",
    ],
    "significance": [0.2, 0.4, 0.6, 0.8],
}

EVENT_DESCRIPTIONS: dict[str, list[str]] = {
    "social": [
        "朋友约周末一起出去玩",
        "同事发消息讨论项目进展",
        "陌生人向你问路",
        "收到同学聚会的邀请",
    ],
    "romantic": [
        "伴侣温柔地注视着你",
        "对方发来一条暧昧的消息",
        "一场意料之外的浪漫晚餐",
        "对方说'我想你了'",
    ],
    "conflict": [
        "激烈争吵中对方说出了伤人的话",
        "两人因为小事发生了争执",
        "被当众质疑和批评",
        "对方摔门而出",
    ],
    "trauma": [
        "噩梦惊醒，想起了过去的事",
        "突然收到令人不安的消息",
        "被触发了不好的回忆",
        "目睹了一场事故",
    ],
    "moral_choice": [
        "必须在两个重要的人之间做出选择",
        "发现朋友在背后说你坏话，你该怎么办",
        "有人要求你说谎保护他",
        "看到不公平的事情发生在眼前",
    ],
    "routine": [
        "今天是普通的一天",
        "路过熟悉的面包店",
        "天气很好，阳光洒在窗台",
        "一个人安静地喝着茶",
    ],
    "betrayal": [
        "发现伴侣和另一个人的暧昧消息",
        "最好的朋友把你的秘密告诉了别人",
        "合作伙伴在背后做了交易",
        "信任的人当众背弃了你",
    ],
}

SCENARIO_TEMPLATES: dict[str, dict] = {
    "anxious_waiting": {
        "event_type": "social",
        "participants": [{"name": "对方", "relation": "partner"}],
        "significance_range": (0.4, 0.7),
        "tags": ["uncertainty", "waiting", "attachment"],
    },
    "romantic_conflict": {
        "event_type": "conflict",
        "participants": [{"name": "对方", "relation": "partner"}],
        "significance_range": (0.6, 0.9),
        "tags": ["conflict", "romantic", "emotional"],
    },
    "moral_dilemma": {
        "event_type": "moral_choice",
        "participants": [{"name": "朋友", "relation": "friend"}],
        "significance_range": (0.7, 0.95),
        "tags": ["moral", "choice", "dilemma"],
    },
    "trauma_trigger": {
        "event_type": "trauma",
        "participants": [],
        "significance_range": (0.7, 0.95),
        "tags": ["trauma", "trigger", "flashback"],
    },
    "intimate_moment": {
        "event_type": "romantic",
        "participants": [{"name": "对方", "relation": "partner"}],
        "significance_range": (0.5, 0.8),
        "tags": ["romantic", "intimate", "love"],
    },
    "routine_event": {
        "event_type": "routine",
        "participants": [],
        "significance_range": (0.1, 0.3),
        "tags": ["routine", "daily", "low_significance"],
    },
}


@dataclass
class GeneratedScenario:
    """动态生成的测试场景。"""
    name: str
    character_state: dict
    event: dict


class ScenarioSampler:
    """采样器——从参数空间生成场景。"""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def sample_params(self, n: int, strategy: str = "lhs") -> list[dict]:
        """采样 n 组角色参数。"""
        if strategy == "lhs":
            return self._latin_hypercube(n)
        return self._uniform_random(n)

    def _latin_hypercube(self, n: int) -> list[dict]:
        """Latin Hypercube Sampling。"""
        dims = {
            k: v for k, v in PARAMETER_SPACE.items()
            if isinstance(v[0], (int, float))
        }
        result = []

        for _ in range(n):
            params: dict = {}
            for dim, values in dims.items():
                interval = 1.0 / n
                offset = self.rng.random() * interval
                idx = min(len(values) - 1,
                          int(self.rng.random() * len(values)))
                params[dim] = values[idx]
            # 分类参数随机选择
            for cat_dim in ["attachment_style", "event_type"]:
                cat_values = PARAMETER_SPACE.get(cat_dim, [])
                if cat_values:
                    params[cat_dim] = self.rng.choice(cat_values)
            params["ace_score"] = self.rng.choice(
                PARAMETER_SPACE.get("ace_score", [0])
            )
            params["significance"] = self.rng.choice(
                PARAMETER_SPACE.get("significance", [0.5])
            )
            result.append(params)

        return result

    def _uniform_random(self, n: int) -> list[dict]:
        """均匀随机采样。"""
        result = []
        for _ in range(n):
            params = {}
            for key, values in PARAMETER_SPACE.items():
                params[key] = self.rng.choice(values)
            result.append(params)
        return result

    def generate_scenarios(self, n: int, strategy: str = "lhs",
                           seed: int = 42) -> list[GeneratedScenario]:
        """生成 n 个完整场景（角色 + 事件）。"""
        self.rng = random.Random(seed)
        params_list = self.sample_params(n, strategy)
        scenarios = []

        for i, params in enumerate(params_list):
            etype = params.get("event_type", "routine")
            desc_options = EVENT_DESCRIPTIONS.get(etype, ["日常事件"])
            description = self.rng.choice(desc_options)

            cs = _build_character_state(params)
            ev = {
                "description": description,
                "type": etype,
                "participants": [],
                "significance": params.get("significance", 0.5),
                "tags": [etype, f"generated_{i}"],
            }

            scenarios.append(GeneratedScenario(
                name=f"generated_{i}_{etype}",
                character_state=cs,
                event=ev,
            ))

        return scenarios


def _build_character_state(params: dict) -> dict:
    """从采样参数构建角色状态。"""
    p = params
    return {
        "name": f"角色_{p.get('name_suffix', '')}",
        "personality": {
            "openness": p.get("openness", 0.5),
            "conscientiousness": p.get("conscientiousness", 0.5),
            "extraversion": p.get("extraversion", 0.5),
            "agreeableness": p.get("agreeableness", 0.5),
            "neuroticism": p.get("neuroticism", 0.5),
            "attachment_style": p.get("attachment_style", "secure"),
        },
        "trauma": {
            "ace_score": p.get("ace_score", 0),
            "active_schemas": _infer_schemas(p),
        },
        "ideal_world": {
            "ideal_self": "被理解和接纳的人",
        },
        "motivation": {
            "current_goal": "理解当前发生的事",
        },
    }


def _infer_schemas(params: dict) -> list[str]:
    """从参数推断可能的图式。"""
    schemas = []
    n = params.get("neuroticism", 0.5)
    a = params.get("agreeableness", 0.5)
    ace = params.get("ace_score", 0)
    attachment = params.get("attachment_style", "secure")

    if n > 0.6:
        schemas.append("缺陷/羞耻")
    if a > 0.7:
        schemas.append("屈从")
    if attachment in ("anxious", "fearful_avoidant"):
        schemas.append("遗弃/不稳定")
    if attachment == "avoidant":
        schemas.append("情感剥夺")
    if ace >= 4:
        schemas.append("不信任/虐待")

    return schemas or []
