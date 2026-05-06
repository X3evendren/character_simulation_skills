"""方案B: 场景矩阵生成器 — 按维度交叉生成综合测试用例。

场景类型(8) × 人格类型(5) × 关系类型(5) × 情绪倾向(3) = 600 组合。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ── Skill → Layer mapping ──
def _skill_to_layer(name: str) -> str:
    mapping = {
        "big_five_analysis": "L0", "attachment_style_analysis": "L0",
        "plutchik_emotion": "L1", "ptsd_trigger_check": "L1", "emotion_probe": "L1",
        "occ_emotion_appraisal": "L2", "cognitive_bias_detect": "L2",
        "defense_mechanism_analysis": "L2", "smith_ellsworth_appraisal": "L2",
        "gottman_interaction": "L3", "marion_erotic_phenomenology": "L3",
        "foucauldian_power_analysis": "L3", "sternberg_triangle": "L3",
        "strogatz_love_dynamics": "L3", "fisher_love_stages": "L3",
        "dirigent_world_tension": "L3", "theory_of_mind": "L3",
        "gross_emotion_regulation": "L4", "kohlberg_moral_reasoning": "L4",
        "maslow_need_stack": "L4", "sdt_motivation_analysis": "L4",
        "young_schema_update": "L5", "ace_trauma_processing": "L5",
        "response_generator": "L5",
    }
    return mapping.get(name, "?")


# ── 人格定义 ──
PERSONALITY_TYPES = {
    "high_neuroticism": {
        "personality": {"openness": 0.4, "conscientiousness": 0.4, "extraversion": 0.35, "agreeableness": 0.55, "neuroticism": 0.80,
                        "attachment_style": "anxious", "defense_style": ["投射", "灾难化"], "cognitive_biases": ["灾难化", "读心术"], "moral_stage": 3},
        "trauma": {"ace_score": 3, "active_schemas": ["遗弃/不稳定", "缺陷/羞耻"], "trauma_triggers": ["被忽视", "被拒绝"]},
        "ideal_world": {"ideal_self": "被坚定选择的、值得被爱的人", "ideal_relationships": "对方永远不会离开"},
    },
    "high_agreeableness": {
        "personality": {"openness": 0.55, "conscientiousness": 0.55, "extraversion": 0.5, "agreeableness": 0.85, "neuroticism": 0.55,
                        "attachment_style": "anxious", "defense_style": ["合理化", "反向形成"], "cognitive_biases": ["个人化"], "moral_stage": 4},
        "trauma": {"ace_score": 1, "active_schemas": ["屈从"], "trauma_triggers": ["被批评"]},
        "ideal_world": {"ideal_self": "被所有人喜欢的、不伤害任何人的存在", "ideal_relationships": "和谐无冲突"},
    },
    "low_agreeableness": {
        "personality": {"openness": 0.45, "conscientiousness": 0.60, "extraversion": 0.55, "agreeableness": 0.20, "neuroticism": 0.35,
                        "attachment_style": "avoidant", "defense_style": ["理智化", "合理化"], "cognitive_biases": ["选择性抽象"], "moral_stage": 2},
        "trauma": {"ace_score": 2, "active_schemas": ["不信任/虐待", "情感剥夺"], "trauma_triggers": ["被利用", "被欺骗"]},
        "ideal_world": {"ideal_self": "掌控一切的强者", "ideal_relationships": "有利可图的关系"},
    },
    "high_conscientiousness": {
        "personality": {"openness": 0.40, "conscientiousness": 0.85, "extraversion": 0.40, "agreeableness": 0.50, "neuroticism": 0.55,
                        "attachment_style": "secure", "defense_style": ["理智化"], "cognitive_biases": ["非黑即白", "应该陈述"], "moral_stage": 4},
        "trauma": {"ace_score": 1, "active_schemas": ["严苛标准"], "trauma_triggers": ["失败", "失去控制"]},
        "ideal_world": {"ideal_self": "完美无缺的、不容失误的人", "ideal_relationships": "有秩序且可预测的关系"},
    },
    "high_openness": {
        "personality": {"openness": 0.85, "conscientiousness": 0.30, "extraversion": 0.60, "agreeableness": 0.60, "neuroticism": 0.55,
                        "attachment_style": "fearful_avoidant", "defense_style": ["升华", "幻想"], "cognitive_biases": ["情绪推理"], "moral_stage": 5},
        "trauma": {"ace_score": 2, "active_schemas": ["情感剥夺"], "trauma_triggers": ["被束缚", "被误解"]},
        "ideal_world": {"ideal_self": "自由不羁的灵魂，不受世俗约束", "ideal_relationships": "灵魂层面的共鸣"},
    },
}

# ── 场景定义 ──
SCENARIO_TYPES = {
    "daily_chat": {"type": "routine", "sig": (0.15, 0.35)},
    "romantic_conflict": {"type": "conflict", "sig": (0.60, 0.85)},
    "romantic_intimate": {"type": "romantic", "sig": (0.45, 0.70)},
    "moral_dilemma": {"type": "moral_choice", "sig": (0.75, 0.95)},
    "authority_encounter": {"type": "conflict", "sig": (0.55, 0.80)},
    "trauma_trigger": {"type": "trauma", "sig": (0.70, 0.95)},
    "reflective_moment": {"type": "reflective", "sig": (0.40, 0.70)},
    "group_social": {"type": "social", "sig": (0.25, 0.50)},
}

RELATION_TYPES = {
    "partner": "伴侣",
    "superior": "上级",
    "friend": "朋友",
    "stranger": "陌生人",
    "family": "家人",
}

EMOTION_TENDENCIES = {
    "positive": ["joy", "trust", "anticipation"],
    "negative": ["sadness", "fear", "anger"],
    "neutral": ["surprise", "trust", "anticipation"],
}

# ── 场景模板 ──
TEMPLATES = {
    ("daily_chat", "partner"): "{name}和伴侣在家里度过普通的晚上，伴侣突然说起今天工作中遇到的困难",
    ("daily_chat", "friend"): "{name}在咖啡馆遇到老朋友，两人聊起最近各自的生活变化",
    ("daily_chat", "family"): "{name}的母亲打来电话，絮叨了半小时家常，最后提起父亲最近身体不太好",
    ("daily_chat", "superior"): "{name}的上司在茶水间随口问起项目的进度",
    ("romantic_conflict", "partner"): "{name}发现伴侣最近频繁看手机，每次走近就锁屏。{name}决定今晚问清楚",
    ("romantic_intimate", "partner"): "深夜，{name}和伴侣躺在床上，窗外下着小雨。伴侣突然说：'我想和你说一件事...'",
    ("moral_dilemma", "friend"): "{name}最好的朋友在工作中做了不道德的事，求{name}帮他隐瞒",
    ("moral_dilemma", "superior"): "{name}发现上司在报告数据上造假，举报就会丢掉工作",
    ("moral_dilemma", "family"): "{name}的弟弟偷了家里的钱去赌博，母亲问{name}知不知道钱去哪了",
    ("authority_encounter", "superior"): "{name}的上司在会议上当着所有人的面批评了{name}的工作成果",
    ("authority_encounter", "stranger"): "{name}在地铁上被态度恶劣的保安拦住要求检查背包",
    ("trauma_trigger", "partner"): "伴侣说：'我需要一点空间思考我们的关系。'然后三天没有回复{name}的消息",
    ("trauma_trigger", "family"): "母亲在电话里说：'你从来都做不好。'这是{name}从小听到大的句子",
    ("reflective_moment", "partner"): "独自走在深夜街头，{name}忽然意识到自己的生活正在偏离真正想要的方向",
    ("reflective_moment", "family"): "春节回家，{name}坐在儿时的房间里，看着老照片，思考这些年变成了什么样的人",
    ("group_social", "friend"): "一群朋友在KTV聚会，有人提议每个人都说说新年计划。轮到{name}了",
    ("group_social", "stranger"): "{name}参加行业交流活动，周围全是陌生人，需要主动攀谈",
    ("daily_chat", "stranger"): "{name}在电梯里遇到新搬来的邻居，对方友好地打了招呼",
    ("romantic_conflict", "friend"): "{name}的好朋友无意中说了一句伤人的话：'你不觉得你太敏感了吗'",
    ("authority_encounter", "partner"): "{name}的伴侣用命令的语气说：'你今晚必须和我一起去那个饭局'",
    ("trauma_trigger", "stranger"): "一个陌生人在街上对{name}大声吼叫，让{name}想起了小时候被父亲打骂的感觉",
    ("reflective_moment", "superior"): "下班后{name}独自坐在办公室，看着窗外的城市灯火，思考自己的职业生涯",
    ("romantic_intimate", "friend"): "{name}的好朋友醉酒后突然说：'其实我喜欢你很久了'",
    ("moral_dilemma", "stranger"): "{name}在路上捡到一个装满现金的钱包，里面有失主的联系方式",
    ("group_social", "partner"): "{name}带伴侣参加公司聚会，同事们开始八卦两人是怎么认识的",
}


def _r(v):
    return round(v, 2)


def generate_cases(sample_per_combo=1, seed=42):
    random.seed(seed)
    cases = []
    cid = 0

    for s_key, s_info in SCENARIO_TYPES.items():
        for p_key, p_data in PERSONALITY_TYPES.items():
            for r_key, r_label in RELATION_TYPES.items():
                for e_key, emotions in EMOTION_TENDENCIES.items():
                    for n in range(sample_per_combo):
                        cid += 1
                        name = f"角色_{cid:04d}"

                        # 场景模板
                        tmpl_key = (s_key, r_key)
                        tmpl = TEMPLATES.get(tmpl_key)
                        if tmpl is None:
                            # 尝试用同场景下任意关系的模板
                            for (sk, rk), t in TEMPLATES.items():
                                if sk == s_key:
                                    tmpl = t
                                    break
                        if tmpl is None:
                            tmpl = f"{name}面对一个需要回应的事件"

                        description = tmpl.format(name=name)
                        lo, hi = s_info["sig"]
                        significance = _r(random.uniform(lo, hi))
                        dominant_emotion = random.choice(emotions)

                        participants = []
                        if r_key != "stranger":
                            participants.append({"name": r_label + f"_{cid}", "relation": r_key if r_key in ("partner", "friend", "family") else r_key})

                        expected = {
                            "big_five_analysis": {"behavioral_bias": {"not_empty": True}},
                            "plutchik_emotion": {"internal": {"dominant": {"in": [dominant_emotion]}}},
                            "response_generator": {"response_text": {"not_empty": True, "length_min": 5}},
                        }
                        # L3 社交/关系层断言
                        if s_key in ("romantic_conflict", "romantic_intimate"):
                            expected["gottman_interaction"] = {"interaction_diagnosis": {"not_empty": True}}
                        if s_key in ("group_social", "daily_chat") and r_key != "stranger":
                            expected["theory_of_mind"] = {"perceived_intentions": {"not_empty": True}}
                        if s_key == "authority_encounter":
                            expected["foucauldian_power_analysis"] = {"power_intensity": {"min": 0.1}}
                        # L2 认知评价层断言
                        if s_key == "moral_dilemma":
                            expected["defense_mechanism_analysis"] = {"detected_defenses": {"not_empty": True}}
                            expected["kohlberg_moral_reasoning"] = {"stage_used": {"not_empty": True}}

                        case = {
                            "id": f"mat_{cid:04d}",
                            "source": "ScenarioMatrix",
                            "domain": s_key,
                            "character_state": {
                                "name": name,
                                "personality": dict(p_data["personality"]),
                                "trauma": dict(p_data["trauma"]),
                                "ideal_world": dict(p_data["ideal_world"]),
                                "motivation": {"current_goal": ""},
                                "emotion_decay": {},
                            },
                            "event": {
                                "description": description,
                                "type": s_info["type"],
                                "participants": participants,
                                "significance": significance,
                                "tags": [s_key, p_key, r_key, e_key],
                            },
                            "expected": expected,
                        }
                        cases.append(case)

    # 去重
    seen = set()
    unique = []
    for c in cases:
        d = c["event"]["description"]
        if d not in seen:
            seen.add(d)
            unique.append(c)
    return unique


def main():
    import argparse
    parser = argparse.ArgumentParser(description="场景矩阵测试用例生成器")
    parser.add_argument("--sample", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cases = generate_cases(sample_per_combo=args.sample, seed=args.seed)
    output_file = OUTPUT_DIR / "scenario_matrix_cases.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    domains = {}
    layers = {}
    for c in cases:
        domains[c["domain"]] = domains.get(c["domain"], 0) + 1
        for skill in c["expected"]:
            layer = _skill_to_layer(skill)
            layers[layer] = layers.get(layer, 0) + 1

    print(f"生成 {len(cases)} 个场景矩阵用例 → {output_file}")
    print(f"领域分布: {dict(sorted(domains.items()))}")
    print(f"层级断言覆盖: {dict(sorted(layers.items()))}")


if __name__ == "__main__":
    main()
