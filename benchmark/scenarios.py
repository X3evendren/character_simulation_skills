"""Benchmark scenarios — diverse character states and events for testing.

Each scenario exercises different parts of the cognitive pipeline.
"""
from __future__ import annotations


def make_base_character_state(overrides: dict | None = None) -> dict:
    """Create a base character state with sensible defaults."""
    cs = {
        "name": "林雨",
        "personality": {
            "openness": 0.6,
            "conscientiousness": 0.5,
            "extraversion": 0.4,
            "agreeableness": 0.55,
            "neuroticism": 0.65,
            "attachment_style": "anxious",
            "defense_style": ["投射", "合理化"],
            "cognitive_biases": ["灾难化", "个人化"],
            "moral_stage": 3,
        },
        "trauma": {
            "ace_score": 2,
            "active_schemas": ["遗弃/不稳定", "屈从"],
            "trauma_triggers": ["被忽视", "被拒绝", "被抛弃"],
        },
        "ideal_world": {
            "ideal_self": "被坚定选择的、无需担心被抛弃的人",
            "ideal_relationships": "当需要时对方总是在身边",
            "ideal_society": "人与人之间有明确的承诺和边界",
        },
        "motivation": {
            "current_goal": "确认对方的感情是否稳定",
            "autonomy_satisfaction": 0.4,
            "competence_satisfaction": 0.5,
            "relatedness_satisfaction": 0.3,
        },
        "emotion_decay": {
            "fast": {"pleasure": -0.1, "arousal": 0.3, "dominance": -0.2},
            "slow": {"pleasure": -0.15, "arousal": 0.2, "dominance": -0.1},
            "last_event_type": "social",
            "events_since_last": 2,
        },
        "personality_state_machine": {
            "baseline": {"openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.4, "agreeableness": 0.55, "neuroticism": 0.65},
            "current_state": "baseline",
            "transition_history": [],
        },
        "relations": {
            "陈风": "partner",
        },
    }
    if overrides:
        _deep_update(cs, overrides)
    return cs


def make_base_event(overrides: dict | None = None) -> dict:
    """Create a base event with sensible defaults."""
    ev = {
        "description": "陈风已经两个小时没有回复消息了。林雨盯着手机屏幕，反复点开他的头像查看最后上线时间。",
        "type": "social",
        "participants": [
            {"name": "陈风", "relation": "partner", "role": "partner"},
        ],
        "significance": 0.5,
        "tags": ["uncertainty", "waiting", "attachment"],
    }
    if overrides:
        _deep_update(ev, overrides)
    return ev


# ── Helpers ──

def _deep_update(d: dict, u: dict) -> dict:
    """Recursively update a dict."""
    for k, v in u.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict):
            _deep_update(d[k], v)
        else:
            d[k] = v
    return d


# ── Scenario definitions ──

SCENARIOS = [
    {
        "name": "anxious_waiting",
        "description": "焦虑型依恋角色等待伴侣回消息",
        "character": make_base_character_state(),
        "event": make_base_event(),
    },
    {
        "name": "romantic_conflict",
        "description": "伴侣说了伤人的话，角色感到被拒绝",
        "character": make_base_character_state(),
        "event": make_base_event({
            "description": "陈风终于回复了，但只有一句'我在忙，别烦我'。林雨感觉胸口被什么击中，手指冰凉。",
            "type": "conflict",
            "significance": 0.7,
            "tags": ["rejection", "conflict", "hurt"],
        }),
    },
    {
        "name": "public_humiliation",
        "description": "在众人面前被权威角色批评",
        "character": make_base_character_state(),
        "event": make_base_event({
            "description": "师父当着所有弟子的面，严厉批评了她的剑法，说她不够专注、不堪大用。所有人都安静了。",
            "type": "social",
            "participants": [
                {"name": "师父", "relation": "superior", "role": "master"},
                {"name": "众弟子", "relation": "peer", "role": "observer"},
            ],
            "significance": 0.8,
            "tags": ["humiliation", "authority", "public"],
        }),
    },
    {
        "name": "moral_dilemma",
        "description": "发现伴侣的秘密，面临道德选择",
        "character": make_base_character_state({
            "personality": {
                "openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.3,
                "agreeableness": 0.6, "neuroticism": 0.7,
                "attachment_style": "fearful_avoidant",
                "defense_style": ["理智化", "反向形成"],
                "cognitive_biases": ["非黑即白", "情绪推理"],
                "moral_stage": 4,
            },
        }),
        "event": make_base_event({
            "description": "她在陈风的外套口袋里发现了一封信，是另一个女人写的。信中提到了一些只有亲密关系中才会有的细节。她必须决定：质问、假装不知道、还是直接离开。",
            "type": "moral_choice",
            "significance": 0.9,
            "tags": ["betrayal", "moral", "secret"],
        }),
    },
    {
        "name": "intimate_moment",
        "description": "伴侣表达了深情的承诺",
        "character": make_base_character_state({
            "personality": {
                "openness": 0.7, "conscientiousness": 0.5, "extraversion": 0.5,
                "agreeableness": 0.7, "neuroticism": 0.5,
                "attachment_style": "anxious",
                "defense_style": ["理想化"],
                "cognitive_biases": ["积极幻觉"],
                "moral_stage": 3,
            },
            "trauma": {
                "ace_score": 1,
                "active_schemas": ["情感剥夺"],
                "trauma_triggers": ["被忽视"],
            },
        }),
        "event": make_base_event({
            "description": "陈风握着她的手，认真地说：'我知道我有时候做得不够好，但我希望你知道——你是我唯一想在一起的人。我不会离开。'",
            "type": "romantic",
            "significance": 0.8,
            "tags": ["commitment", "intimacy", "emotional"],
        }),
    },
    {
        "name": "threat_encounter",
        "description": "角色感到人身安全的威胁",
        "character": make_base_character_state({
            "personality": {
                "openness": 0.4, "conscientiousness": 0.3, "extraversion": 0.2,
                "agreeableness": 0.3, "neuroticism": 0.85,
                "attachment_style": "fearful_avoidant",
                "defense_style": ["分裂", "投射性认同"],
                "cognitive_biases": ["灾难化", "选择性抽象"],
                "moral_stage": 2,
            },
            "trauma": {
                "ace_score": 4,
                "active_schemas": ["不信任/虐待", "缺陷/羞耻"],
                "trauma_triggers": ["被跟踪", "被威胁", "黑暗"],
            },
        }),
        "event": make_base_event({
            "description": "深夜独自回家，她注意到有人在跟踪她。脚步声越来越近，她的心跳如鼓，手开始发抖。",
            "type": "threat",
            "participants": [
                {"name": "未知跟踪者", "relation": "stranger", "role": "threat"},
            ],
            "significance": 0.85,
            "tags": ["danger", "fear", "threat"],
        }),
    },
    {
        "name": "low_significance_routine",
        "description": "日常琐事，低显著性",
        "character": make_base_character_state(),
        "event": make_base_event({
            "description": "早上起床，窗外下着小雨。今天没有什么特别的安排。",
            "type": "routine",
            "participants": [],
            "significance": 0.1,
            "tags": ["routine", "mundane"],
        }),
    },
    {
        "name": "group_social",
        "description": "群体社交场景，多人互动",
        "character": make_base_character_state({
            "personality": {
                "openness": 0.55, "conscientiousness": 0.5, "extraversion": 0.35,
                "agreeableness": 0.6, "neuroticism": 0.6,
                "attachment_style": "avoidant",
                "defense_style": ["退缩", "理智化"],
                "cognitive_biases": ["读心术", "个人化"],
                "moral_stage": 3,
            },
        }),
        "event": make_base_event({
            "description": "一群同门师兄弟在讨论下个月的宗门大比。每个人都在讨论自己的准备情况。有人看向她，问她打算参加吗。",
            "type": "social",
            "participants": [
                {"name": "大师兄", "relation": "peer", "role": "senior"},
                {"name": "三师姐", "relation": "peer", "role": "peer"},
                {"name": "小师弟", "relation": "peer", "role": "junior"},
            ],
            "significance": 0.4,
            "tags": ["group", "social_pressure", "competition"],
        }),
    },
]


def get_scenarios() -> list[dict]:
    """Return all benchmark scenarios."""
    return SCENARIOS
