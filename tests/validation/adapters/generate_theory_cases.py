"""基于心理学文献批量生成理论真值验证用例。

覆盖缺乏标注数据集的维度:
- 依恋风格 (Bowlby, Ainsworth)
- PTSD/ACE (DSM-5, Felitti)
- Kohlberg 道德推理
- Theory of Mind
- Gottman 冲突模式
- 认知偏差 (Beck, Burns)
- 防御机制 (Anna Freud, Vaillant)
- Plutchik 情感组合
"""
import json
import itertools
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ═══════════════════════════════════════════════════════
# 基础模板
# ═══════════════════════════════════════════════════════

ATTACHMENT_STYLES = {
    "secure": {"neuroticism": 0.35, "agreeableness": 0.65, "extraversion": 0.6},
    "anxious": {"neuroticism": 0.75, "agreeableness": 0.7, "extraversion": 0.5},
    "avoidant": {"neuroticism": 0.45, "agreeableness": 0.35, "extraversion": 0.25},
    "fearful_avoidant": {"neuroticism": 0.8, "agreeableness": 0.4, "extraversion": 0.2},
}

ATTACHMENT_TRIGGERS = {
    "感知到被忽视": {
        "event": "伴侣连续两天没有主动发消息，在社交媒体上却能正常发帖。角色发消息过去只得到一个字的回复。",
        "type": "social",
        "anxious": {"activation_min": 0.65, "dominant_emotion": ["fear", "sadness"], "bias": ["灾难化", "读心术"]},
        "avoidant": {"activation_min": 0.5, "dominant_emotion": ["disgust", "anger"], "defense": ["情感隔离", "理智化"]},
        "secure": {"activation_max": 0.5, "dominant_emotion": ["surprise", "trust"]},
        "fearful_avoidant": {"activation_min": 0.7, "dominant_emotion": ["fear", "anger"], "defense": ["分裂", "投射"]},
    },
    "亲密要求": {
        "event": "伴侣深情地说：'我觉得我们之间总有一道墙。我想更了解你，想知道你的一切。你愿意向我打开心扉吗？'",
        "type": "romantic",
        "anxious": {"activation_min": 0.4, "dominant_emotion": ["joy", "fear"]},
        "avoidant": {"activation_min": 0.6, "dominant_emotion": ["fear", "disgust"], "defense": ["情感隔离", "退缩"]},
        "secure": {"activation_min": 0.3, "dominant_emotion": ["joy", "trust"]},
        "fearful_avoidant": {"activation_min": 0.7, "dominant_emotion": ["fear", "joy"], "defense": ["反向形成", "理智化"]},
    },
    "冲突后修复请求": {
        "event": "激烈争吵后的第二天，伴侣端着一杯热咖啡走过来，轻声说：'昨晚我话说重了，对不起。我们能谈谈吗？'",
        "type": "conflict",
        "anxious": {"activation_min": 0.5, "dominant_emotion": ["joy", "fear"]},
        "avoidant": {"activation_min": 0.5, "dominant_emotion": ["fear", "trust"], "defense": ["退缩"]},
        "secure": {"activation_max": 0.5, "dominant_emotion": ["trust", "joy"]},
        "fearful_avoidant": {"activation_min": 0.6, "dominant_emotion": ["fear", "joy"], "defense": ["投射", "合理化"]},
    },
    "第三者威胁": {
        "event": "在派对上，一个很有魅力的人与角色伴侣相谈甚欢，肢体语言亲密。伴侣似乎很享受这种关注。",
        "type": "social",
        "anxious": {"activation_min": 0.8, "dominant_emotion": ["fear", "anger", "sadness"]},
        "avoidant": {"activation_min": 0.5, "dominant_emotion": ["disgust", "anger"]},
        "secure": {"activation_max": 0.5, "dominant_emotion": ["surprise", "trust"]},
        "fearful_avoidant": {"activation_min": 0.8, "dominant_emotion": ["fear", "anger", "disgust"]},
    },
    "对方失踪": {
        "event": "伴侣说去出差三天，但已经五天了还没回来，手机也关机。角色的消息全部未读。",
        "type": "social",
        "anxious": {"activation_min": 0.9, "dominant_emotion": ["fear", "sadness"]},
        "avoidant": {"activation_min": 0.4, "dominant_emotion": ["anger", "disgust"], "defense": ["理智化"]},
        "secure": {"activation_max": 0.6, "dominant_emotion": ["fear", "trust"]},
        "fearful_avoidant": {"activation_min": 0.85, "dominant_emotion": ["fear", "sadness", "anger"]},
    },
}

COGNITIVE_BIASES = {
    "灾难化": {
        "event": "老板说'明天早上到我办公室来一趟'，没有说明原因。",
        "expected_biases": ["灾难化"],
        "evidence": "weak",
    },
    "读心术": {
        "event": "朋友今天没有像往常一样打招呼，径直走过。",
        "expected_biases": ["读心术", "个人化"],
        "evidence": "weak",
    },
    "非黑即白": {
        "event": "考试得了85分，而目标是90分。",
        "expected_biases": ["非黑即白", "完美主义"],
        "evidence": "weak",
    },
    "情绪推理": {
        "event": "角色感到非常焦虑和不安，因此断定即将发生糟糕的事情。",
        "expected_biases": ["情绪推理"],
        "evidence": "weak",
    },
    "过度概括": {
        "event": "第一次约会被拒绝后，角色认为'我永远也找不到对象了'。",
        "expected_biases": ["过度概括", "灾难化"],
        "evidence": "weak",
    },
    "个人化": {
        "event": "伴侣心情不好不说话。角色想：'一定是我做错了什么。'",
        "expected_biases": ["个人化", "读心术"],
        "evidence": "weak",
    },
}

MORAL_DILEMMAS = [
    {
        "stage": 2,
        "event": "角色发现可以偷取富人的食物分给饥饿的流浪儿，而且不会被发现。",
        "expected_stage": [2, 3],
        "expected_keywords": ["惩罚", "奖励", "交换", "好处"],
    },
    {
        "stage": 3,
        "event": "角色的好朋友请求在考试中帮忙作弊，因为如果挂科就会失去奖学金。",
        "expected_stage": [3],
        "expected_keywords": ["朋友", "关系", "期望", "好人"],
    },
    {
        "stage": 4,
        "event": "角色发现公司CEO在逃税，但举报会毁掉整个公司和数千员工的生计。",
        "expected_stage": [4, 3],
        "expected_keywords": ["法律", "秩序", "规则", "社会"],
    },
    {
        "stage": 5,
        "event": "一项法律明显歧视少数群体。角色是执法者，必须决定是否执行。",
        "expected_stage": [5, 4],
        "expected_keywords": ["权利", "正义", "契约", "改变"],
    },
    {
        "stage": 5,
        "event": "为了挽救五条生命，是否应该未经同意使用一个人的器官？（这个人恰好匹配所有五人）",
        "expected_stage": [5],
        "expected_keywords": ["生命", "权利", "功利", "原则"],
    },
]

EMOTIONAL_SCENARIOS = [
    ("joy", "角色经过十年努力终于实现了儿时的梦想，在领奖台上百感交集。"),
    ("joy", "多年未见的挚友突然出现在家门口，手中提着角色最喜欢的食物。"),
    ("sadness", "角色翻看已故母亲的旧照片，发现了一张从未见过的合影。"),
    ("sadness", "最亲密的朋友搬去了另一个城市，临别时只说了句'保重'。"),
    ("fear", "深夜独自加班时，走廊尽头传来沉重的脚步声，越来越近。"),
    ("fear", "医生面色凝重地走进病房，手里拿着一份检查报告。"),
    ("anger", "有人当面侮辱角色的家人，还带着轻蔑的笑容。"),
    ("anger", "同事窃取了角色准备了三个月的项目方案，在会议上作为自己的成果展示。"),
    ("disgust", "发现一直信任的伙伴在背后散布恶毒的谣言。"),
    ("surprise", "一个一直在社交媒体关注角色的人突然出现在现实中，准确说出了角色从未公开过的个人信息。"),
    ("trust", "在角色最脆弱的时候，一个意想不到的人伸出了援手。"),
    ("anticipation", "角色准备了数月的重大考试就在明天，昨夜辗转难眠。"),
]

GOTTMAN_PATTERNS = [
    {
        "name": "criticism_defensiveness",
        "event": "伴侣说：'你永远都是这样，从来不考虑我的感受！'角色反驳：'我哪有永远这样？你才是那个总是指责别人的人！'",
        "expected_horsemen": ["criticism", "defensiveness"],
        "repair_detected": False,
    },
    {
        "name": "contempt_stonewalling",
        "event": "伴侣冷笑着说：'就你这种水平也好意思说？真可笑。'角色沉默不语，转身走开。",
        "expected_horsemen": ["contempt", "stonewalling"],
        "repair_detected": False,
    },
    {
        "name": "repair_attempt",
        "event": "争吵中伴侣突然停下来，说：'等一下，我们都在气头上。我不想伤害你。让我冷静一下我们再谈好吗？'",
        "expected_horsemen": [],
        "repair_detected": True,
    },
    {
        "name": "healthy_interaction",
        "event": "伴侣说：'你最近工作很忙，我感到有些被忽视。'角色回应：'谢谢你告诉我。我们这周末好好待一天，只属于我们两个。'",
        "expected_horsemen": [],
        "repair_detected": False,
    },
]

PTSD_SCENARIOS = [
    {
        "ace": 4,
        "triggers": ["被控制", "暴力", "黑暗"],
        "event": "有人在狭窄的走廊里抓住角色的手腕不放。",
        "expected_triggered": True,
        "expected_hyperarousal_min": 0.6,
    },
    {
        "ace": 5,
        "triggers": ["被忽视", "被抛弃", "被拒绝"],
        "event": "唯一的支持者突然失联了三天，所有求助都没有回应。",
        "expected_triggered": True,
        "expected_intrusion_min": 0.5,
    },
    {
        "ace": 3,
        "triggers": ["被羞辱", "公开场合"],
        "event": "在团队会议上，领导点名批评角色的工作成果'毫无价值'。",
        "expected_triggered": True,
        "expected_avoidance_min": 0.4,
    },
    {
        "ace": 1,
        "triggers": ["被威胁"],
        "event": "同事开玩笑地用拳头比划了一下。",
        "expected_triggered": False,
        "expected_hyperarousal_max": 0.5,
    },
]


def make_base_char(overrides=None):
    c = {
        "personality": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                        "agreeableness": 0.5, "neuroticism": 0.5,
                        "attachment_style": "secure", "defense_style": [], "cognitive_biases": [],
                        "moral_stage": 3},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {}, "motivation": {"current_goal": ""}, "emotion_decay": {},
    }
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(c.get(k), dict):
                c[k].update(v)
            else:
                c[k] = v
    return c


def generate_attachment_cases():
    cases = []
    for style, traits in ATTACHMENT_STYLES.items():
        for trigger_name, trigger_data in ATTACHMENT_TRIGGERS.items():
            expected_response = trigger_data.get(style)
            if expected_response is None:
                continue
            profile = dict(traits)
            profile["attachment_style"] = style
            profile["cognitive_biases"] = ["灾难化"] if style in ("anxious", "fearful_avoidant") else []

            case = {
                "id": f"att_{style}_{trigger_name}",
                "source": f"Attachment Theory (Bowlby/Ainsworth) — {style} × {trigger_name}",
                "character_state": {
                    "name": f"{style}型角色",
                    **make_base_char({"personality": profile}),
                },
                "event": {
                    "description": trigger_data["event"],
                    "type": trigger_data["type"],
                    "participants": [{"name": "伴侣", "relation": "partner", "role": "partner"}],
                    "significance": 0.6,
                    "tags": ["attachment", style, trigger_name],
                },
                "expected": {
                    "attachment_style_analysis": {},
                    "response_generator": {"response_text": {"not_empty": True}},
                },
            }

            # 依恋激活水平
            if "activation_min" in expected_response:
                case["expected"]["attachment_style_analysis"]["activation_level"] = {"min": expected_response["activation_min"]}
            if "activation_max" in expected_response:
                case["expected"]["attachment_style_analysis"]["activation_level"] = {"max": expected_response["activation_max"]}

            # 主导情绪
            if "dominant_emotion" in expected_response:
                case["expected"]["plutchik_emotion"] = {
                    "internal.dominant": {"in": expected_response["dominant_emotion"]},
                }

            # 防御机制
            if "defense" in expected_response:
                case["expected"]["defense_mechanism_analysis"] = {
                    "activated_defense.name": {"in": expected_response["defense"] + ["未检测到"]},
                }

            # 认知偏差
            if "bias" in expected_response:
                case["expected"]["cognitive_bias_detect"] = {
                    "activated_biases": {"contains_any": expected_response["bias"]},
                }

            cases.append(case)
    return cases


def generate_bias_cases():
    cases = []
    for bias_name, bias_data in COGNITIVE_BIASES.items():
        profile = make_base_char({
            "personality": {
                "neuroticism": 0.75,
                "cognitive_biases": [bias_name],
            }
        })
        case = {
            "id": f"bias_{bias_name}",
            "source": f"Cognitive Bias Theory (Beck/Burns) — {bias_name}",
            "character_state": {
                "name": f"{bias_name}角色",
                **profile,
            },
            "event": {
                "description": bias_data["event"],
                "type": "social",
                "participants": [],
                "significance": 0.5,
                "tags": ["cognitive_bias", bias_name],
            },
            "expected": {
                "cognitive_bias_detect": {
                    "activated_biases": {"contains_any": bias_data["expected_biases"]},
                },
                "response_generator": {"response_text": {"not_empty": True}},
            },
        }
        cases.append(case)
    return cases


def generate_moral_cases():
    cases = []
    for dilemma in MORAL_DILEMMAS:
        stage = dilemma["stage"]
        profile = make_base_char({"personality": {"moral_stage": stage}})
        case = {
            "id": f"moral_stage{stage}",
            "source": f"Kohlberg Moral Development — Stage {stage}",
            "character_state": {
                "name": f"阶段{stage}角色",
                **profile,
            },
            "event": {
                "description": dilemma["event"],
                "type": "moral_choice",
                "participants": [],
                "significance": 0.85,
                "tags": ["moral_dilemma", f"stage_{stage}"],
            },
            "expected": {
                "kohlberg_moral_reasoning": {
                    "stage_used": {"in": dilemma["expected_stage"]},
                    "reasoning": {"contains_any": dilemma["expected_keywords"]},
                    "moral_conflict": {"not_empty": True},
                },
                "response_generator": {"response_text": {"not_empty": True}},
            },
        }
        cases.append(case)

    # 每个阶段多几个变体
    for stage in [2, 3, 4, 5]:
        for variant in range(2):
            extra_dilemmas = {
                2: ["可以无风险地从富人那里偷东西给穷人", "如果能获得巨大奖励但有轻微违规风险"],
                3: ["最好的朋友需要帮忙隐瞒一个会让他丢脸的真相", "社区期望角色做某事但角色内心不愿意"],
                4: ["发现同事违规操作但举报会破坏团队和谐", "一项地方法规与个人便利产生冲突"],
                5: ["一项法律保护了多数人但严重损害少数群体", "为了更大的社会公正是否应该违反现有契约"],
            }
            case = {
                "id": f"moral_stage{stage}_v{variant}",
                "source": f"Kohlberg Moral Development — Stage {stage}, Variant {variant}",
                "character_state": {
                    "name": f"阶段{stage}角色{variant}",
                    **make_base_char({"personality": {"moral_stage": stage}}),
                },
                "event": {
                    "description": extra_dilemmas[stage][variant],
                    "type": "moral_choice",
                    "participants": [],
                    "significance": 0.8,
                    "tags": ["moral_dilemma", f"stage_{stage}"],
                },
                "expected": {
                    "kohlberg_moral_reasoning": {
                        "stage_used": {"min": stage - 1, "max": stage + 1},
                        "moral_conflict": {"not_empty": True},
                    },
                    "response_generator": {"response_text": {"not_empty": True}},
                },
            }
            cases.append(case)
    return cases


def generate_emotion_cases():
    cases = []
    for emotion, event_desc in EMOTIONAL_SCENARIOS:
        profile = make_base_char({"personality": {"neuroticism": 0.5}})
        case = {
            "id": f"emo_{emotion}_{len(cases)}",
            "source": f"Plutchik Emotion Theory — {emotion}",
            "character_state": {
                "name": "角色",
                **profile,
            },
            "event": {
                "description": event_desc,
                "type": "social",
                "participants": [],
                "significance": 0.7,
                "tags": ["emotion", emotion],
            },
            "expected": {
                "plutchik_emotion": {
                    "internal.dominant": {"in": [emotion]},
                    "internal.intensity": {"min": 0.4},
                },
                "response_generator": {"response_text": {"not_empty": True}},
            },
        }
        cases.append(case)

    # 复合情感
    complex_emotions = [
        ("love", "joy+trust", "角色看着伴侣熟睡的脸，想起多年来的点点滴滴。"),
        ("guilt", "sadness+fear", "角色无意中看到了朋友的秘密日记，里面写满了对自己的不满。"),
        ("shame", "sadness+disgust", "角色在重要演讲中忘词，全场安静地注视着她。"),
        ("jealousy", "anger+fear+sadness", "角色看到前任在社交媒体上和新恋人甜蜜合照。"),
        ("awe", "surprise+fear", "角色第一次站在珠穆朗玛峰大本营，仰望世界之巅。"),
        ("despair", "sadness+fear", "连续被十家公司拒绝后，角色看着空荡荡的银行账户。"),
        ("hope", "anticipation+trust", "医生微笑着说：'最新检查结果出来了，情况比预期的好。'"),
        ("gratitude", "joy+trust", "角色患重病期间，所有朋友轮流来照顾，从未抱怨。"),
    ]
    for name, components, event_desc in complex_emotions:
        case = {
            "id": f"emo_complex_{name}",
            "source": f"Plutchik Complex Emotion — {name} ({components})",
            "character_state": {
                "name": "角色",
                **make_base_char(),
            },
            "event": {
                "description": event_desc,
                "type": "social",
                "participants": [],
                "significance": 0.7,
                "tags": ["emotion", "complex", name],
            },
            "expected": {
                "plutchik_emotion": {
                    "internal.intensity": {"min": 0.4},
                },
                "response_generator": {"response_text": {"not_empty": True}},
            },
        }
        cases.append(case)
    return cases


def generate_gottman_cases():
    cases = []
    for pattern in GOTTMAN_PATTERNS:
        case = {
            "id": f"gottman_{pattern['name']}",
            "source": f"Gottman Method — {pattern['name']}",
            "character_state": {
                "name": "角色",
                **make_base_char({"personality": {"agreeableness": 0.4, "neuroticism": 0.65}}),
            },
            "event": {
                "description": pattern["event"],
                "type": "conflict",
                "participants": [{"name": "伴侣", "relation": "partner", "role": "partner"}],
                "significance": 0.7,
                "tags": ["gottman", pattern["name"]],
            },
            "expected": {
                "gottman_interaction": {
                    "active_horsemen": {
                        "contains_all": pattern["expected_horsemen"],
                    } if pattern["expected_horsemen"] else {"equals": []},
                    "repair_attempt_detected": {"equals": pattern["repair_detected"]},
                    "interaction_diagnosis": {"not_empty": True},
                },
                "response_generator": {"response_text": {"not_empty": True}},
            },
        }
        cases.append(case)
    return cases


def generate_ptsd_cases():
    cases = []
    for scenario in PTSD_SCENARIOS:
        case = {
            "id": f"ptsd_ace{scenario['ace']}_{len(cases)}",
            "source": f"PTSD/ACE Theory — ACE={scenario['ace']}",
            "character_state": {
                "name": f"ACE{scenario['ace']}角色",
                **make_base_char({
                    "personality": {"neuroticism": 0.4 + scenario["ace"] * 0.08},
                    "trauma": {
                        "ace_score": scenario["ace"],
                        "active_schemas": [],
                        "trauma_triggers": scenario["triggers"],
                    },
                }),
            },
            "event": {
                "description": scenario["event"],
                "type": "threat",
                "participants": [],
                "significance": 0.75,
                "tags": ["ptsd", "trauma", f"ace_{scenario['ace']}"],
            },
            "expected": {
                "ptsd_trigger_check": {
                    "triggered": {"equals": scenario["expected_triggered"]},
                },
                "response_generator": {"response_text": {"not_empty": True}},
            },
        }
        if "expected_hyperarousal_min" in scenario:
            case["expected"]["ptsd_trigger_check"]["hyperarousal_risk"] = {"min": scenario["expected_hyperarousal_min"]}
        if "expected_hyperarousal_max" in scenario:
            case["expected"]["ptsd_trigger_check"]["hyperarousal_risk"] = {"max": scenario["expected_hyperarousal_max"]}
        if "expected_intrusion_min" in scenario:
            case["expected"]["ptsd_trigger_check"]["intrusion_risk"] = {"min": scenario["expected_intrusion_min"]}
        if "expected_avoidance_min" in scenario:
            case["expected"]["ptsd_trigger_check"]["avoidance_risk"] = {"min": scenario["expected_avoidance_min"]}
        cases.append(case)
    return cases


if __name__ == "__main__":
    all_cases = []
    all_cases.extend(generate_attachment_cases())
    all_cases.extend(generate_bias_cases())
    all_cases.extend(generate_moral_cases())
    all_cases.extend(generate_emotion_cases())
    all_cases.extend(generate_gottman_cases())
    all_cases.extend(generate_ptsd_cases())

    print(f"Generated {len(all_cases)} theory-grounded cases")

    # 统计
    by_type = {}
    for c in all_cases:
        t = c["id"].split("_")[0]
        by_type[t] = by_type.get(t, 0) + 1
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")

    out_path = OUTPUT_DIR / "theory_grounded_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")
