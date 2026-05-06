"""从 PersonalityEvd 数据集提取 Big Five 验证用例。

PersonalityEvd (EMNLP 2024): 中文电视剧对话，每轮对话标注 Big Five 五个维度。
来源: https://github.com/Lei-Sun-RUC/PersonalityEvd

输出: 我们的验证用例格式 (character_state + event + expected)
"""
import json
import os
import sys
from pathlib import Path

import glob as _glob
_tmp = Path(os.environ.get("TEMP", "/tmp"))
DATASET_DIR = _tmp / "PersonalityEvd" / "Dataset"
if not DATASET_DIR.exists():
    # 尝试其他位置
    DATASET_DIR = Path("/tmp/PersonalityEvd/Dataset")
OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# 大五级别映射
LEVEL_MAP = {
    "开放性高": ("openness", 0.75),
    "开放性低": ("openness", 0.25),
    "尽责性高": ("conscientiousness", 0.8),
    "尽责性低": ("conscientiousness", 0.25),
    "外向性高": ("extraversion", 0.75),
    "外向性低": ("extraversion", 0.25),
    "宜人性高": ("agreeableness", 0.75),
    "宜人性低": ("agreeableness", 0.25),
    "神经质性高": ("neuroticism", 0.75),
    "神经质性低": ("neuroticism", 0.25),
}

# 大五维度 → Big Five Skill 预期行为偏置
TRAIT_BIAS_MAP = {
    "neuroticism_high": {
        "emotional_reactivity_min": 0.5,
        "interpretation_direction": "negative",
        "stress_keywords": ["焦虑", "担忧", "紧张", "恐慌", "不安"],
    },
    "neuroticism_low": {
        "emotional_reactivity_max": 0.5,
        "stress_keywords": ["冷静", "稳定", "理性", "平和"],
    },
    "agreeableness_high": {
        "social_approach": ["cooperative", "accommodating", "warm"],
        "conflict_style": ["妥协", "让步", "迎合"],
    },
    "agreeableness_low": {
        "social_approach": ["confrontational", "competitive", "skeptical"],
        "conflict_style": ["对抗", "质疑", "坚持己见"],
    },
    "conscientiousness_high": {
        "decision_style": ["deliberate", "cautious", "planful"],
    },
    "extraversion_low": {
        "social_approach": ["avoid", "withdraw", "reserved"],
    },
}


def load_dialogues():
    with open(DATASET_DIR / "dialogue.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_annotations(task="EPR-State Task"):
    annotations = {}
    for split in ["train_annotation.json", "valid_annotation.json", "test_annotation.json"]:
        path = DATASET_DIR / task / split
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                annotations.update(data)
    return annotations


def extract_personality_profile(annotation_entry: dict) -> dict:
    """从单轮对话的标注中提取大五人格档案。"""
    profile = {
        "openness": 0.5, "conscientiousness": 0.5,
        "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5,
    }
    trait_info = {}
    for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
        ann = annotation_entry.get(trait, {})
        level = ann.get("level", "无法判断")
        evidence = ann.get("utt_id", "")
        nat_lang = ann.get("nat_lang", "")
        key = f"{trait}_{level}"
        if trait == "openness":
            map_key = f"开放性{level.replace('开放性', '')}" if "开放性" in level else None
        elif trait == "conscientiousness":
            map_key = f"尽责性{level.replace('尽责性', '')}" if "尽责性" in level else None
        elif trait == "extraversion":
            map_key = f"外向性{level.replace('外向性', '')}" if "外向性" in level else None
        elif trait == "agreeableness":
            map_key = f"宜人性{level.replace('宜人性', '')}" if "宜人性" in level else None
        elif trait == "neuroticism":
            map_key = f"神经质性{level.replace('神经质性', '')}" if "神经质性" in level else None
        else:
            map_key = None

        if map_key and map_key in LEVEL_MAP:
            trait_name, value = LEVEL_MAP[map_key]
            profile[trait_name] = value
            trait_info[trait] = {"level": level, "value": value, "evidence": evidence, "reason": nat_lang[:100]}

    return profile, trait_info


def build_expected(trait_info: dict) -> dict:
    """根据人格标注构建预期断言。"""
    expected = {"big_five_analysis": {}, "response_generator": {"response_text": {"not_empty": True}}}

    ba = expected["big_five_analysis"]

    # 神经质 → 情绪反应
    if "neuroticism" in trait_info:
        ti = trait_info["neuroticism"]
        if ti["level"] == "神经质性高":
            ba["emotional_reactivity"] = {"min": 0.5}
            ba["stress_response"] = {"keywords": ["焦虑", "担忧", "紧张", "不安", "敏感"]}
        elif ti["level"] == "神经质性低":
            ba["emotional_reactivity"] = {"max": 0.5}

    # 宜人性 → 社交方式
    if "agreeableness" in trait_info:
        ti = trait_info["agreeableness"]
        if ti["level"] == "宜人性高":
            ba["social_approach"] = {"in": ["cooperative", "accommodating", "warm", "approach"]}
        elif ti["level"] == "宜人性低":
            ba["social_approach"] = {"in": ["confrontational", "competitive", "skeptical", "avoid"]}

    # 尽责性 → 决策风格
    if "conscientiousness" in trait_info:
        ti = trait_info["conscientiousness"]
        if ti["level"] == "尽责性高":
            ba["decision_style"] = {"in": ["deliberate", "cautious", "planful"]}

    return expected


def extract_cases(limit_per_character: int = 5) -> list[dict]:
    """从 PersonalityEvd 提取验证用例。"""
    dialogues = load_dialogues()
    annotations = load_annotations()
    cases = []

    for char_name, char_data in annotations.items():
        if char_name not in dialogues:
            continue

        char_dialogue = dialogues[char_name]
        dlg_list = char_dialogue.get("dialogue", {})

        count = 0
        for turn_id, turn_data in char_data.get("annotation", {}).items():
            if count >= limit_per_character:
                break

            turn_id_str = str(turn_id)
            if turn_id_str not in dlg_list:
                continue

            # 获取对话内容作为事件上下文
            utterances = dlg_list[turn_id_str]
            if isinstance(utterances, list):
                dialogue_text = " ".join(utterances[:6])  # 取前6句作为上下文
            else:
                dialogue_text = str(utterances)

            profile, trait_info = extract_personality_profile(turn_data)

            # 跳过所有维度都"无法判断"的轮次
            if len(trait_info) == 0:
                continue

            expected = build_expected(trait_info)

            case = {
                "id": f"pevd_{char_name}_{turn_id}",
                "source": f"PersonalityEvd (EMNLP 2024) — {char_name}, 第{turn_id}轮",
                "character_state": {
                    "name": char_name,
                    "personality": {
                        **profile,
                        "attachment_style": "secure",
                        "defense_style": [],
                        "cognitive_biases": [],
                        "moral_stage": 3,
                    },
                    "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
                    "ideal_world": {},
                    "motivation": {"current_goal": ""},
                    "emotion_decay": {},
                },
                "event": {
                    "description": f"电视剧对话场景 — {dialogue_text[:200]}",
                    "type": "social",
                    "participants": [],
                    "significance": 0.5,
                    "tags": ["dialogue", "tv_drama"],
                },
                "expected": expected,
                "_trait_info": {k: v["level"] for k, v in trait_info.items()},
            }
            cases.append(case)
            count += 1

    return cases


if __name__ == "__main__":
    cases = extract_cases(limit_per_character=5)
    print(f"Extracted {len(cases)} cases from PersonalityEvd")

    # 统计
    total_traits = sum(len(c["_trait_info"]) for c in cases)
    print(f"Total trait annotations: {total_traits}")
    print(f"Avg traits per case: {total_traits/max(len(cases),1):.1f}")

    # 保存
    out_path = OUTPUT_DIR / "personality_evd_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")
