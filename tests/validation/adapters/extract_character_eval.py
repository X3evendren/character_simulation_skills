"""从 CharacterEval 数据集提取角色一致性验证用例。

CharacterEval (2024): 77个中文小说/电视剧角色, 1,785条对话, MBTI标注。
来源: https://github.com/morecry/CharacterEval

输出: 验证用例格式
"""
import json
import os
from pathlib import Path

_tmp = Path(os.environ.get("TEMP", "/tmp"))
DATASET_DIR = _tmp / "CharacterEval" / "data"
if not DATASET_DIR.exists():
    DATASET_DIR = Path("/tmp/CharacterEval/data")
OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# MBTI → 大五近似映射 (基于 Furnham, 1996; McCrae & Costa, 1989)
MBTI_TO_BIG5 = {
    "E": ("extraversion", 0.7, 0.5, 0.9),
    "I": ("extraversion", 0.25, 0.1, 0.45),
    "S": ("openness", 0.35, 0.15, 0.55),
    "N": ("openness", 0.7, 0.55, 0.9),
    "T": ("agreeableness", 0.35, 0.15, 0.55),
    "F": ("agreeableness", 0.7, 0.55, 0.9),
    "J": ("conscientiousness", 0.75, 0.6, 0.9),
    "P": ("conscientiousness", 0.3, 0.1, 0.5),
}

# MBTI → 预期行为偏置
MBTI_BEHAVIOR = {
    "E": {"social_approach": ["approach", "outgoing"], "decision_style": ["talkative", "expressive"]},
    "I": {"social_approach": ["avoid", "withdraw"], "decision_style": ["reserved", "reflective"]},
    "T": {"interpretation_bias": ["logic", "analysis", "objective"]},
    "F": {"interpretation_bias": ["empathy", "harmony", "values"]},
    "J": {"stress_response": ["plan", "control", "structure"]},
    "P": {"stress_response": ["adapt", "flexible", "spontaneous"]},
}


def load_test_data():
    path = DATASET_DIR / "test_data.jsonl"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if raw.startswith("["):
            return json.loads(raw)
        # 逐行 JSONL 格式
        data = []
        for line in raw.split("\n"):
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return data


def load_character_profiles():
    path = DATASET_DIR / "character_profiles.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def mbti_to_personality(mbti: str) -> dict:
    """将 MBTI 类型映射到大五人格数值。"""
    profile = {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5}
    if not mbti or len(mbti) < 4:
        return profile

    for letter in mbti[:4]:
        letter = letter.upper()
        if letter in MBTI_TO_BIG5:
            trait, value, _, _ = MBTI_TO_BIG5[letter]
            profile[trait] = value

    return profile


def extract_cases() -> list[dict]:
    test_data = load_test_data()
    profiles = load_character_profiles()
    cases = []

    for item in test_data:
        role = item.get("role", "")
        context = item.get("context", "")
        if not role or not context:
            continue

        # 获取角色档案
        char_profile = profiles.get(role, {})
        mbti = char_profile.get("mbti", "")
        personality = mbti_to_personality(mbti)

        # 提取对话中的关键事件
        lines = context.split("\n")
        if len(lines) < 2:
            continue
        # 取最后几行作为"当前事件"
        recent_lines = lines[-4:] if len(lines) >= 4 else lines
        event_desc = " — ".join(recent_lines)[:300]

        # 构建预期
        expected = {
            "big_five_analysis": {},
            "response_generator": {"response_text": {"not_empty": True}},
        }

        if mbti:
            for letter in mbti[:4]:
                letter = letter.upper()
                if letter in MBTI_BEHAVIOR:
                    for field, rule in MBTI_BEHAVIOR[letter].items():
                        if field == "social_approach":
                            expected["big_five_analysis"]["social_approach"] = {"in": rule}
                        elif field == "decision_style":
                            expected["big_five_analysis"]["decision_style"] = {"in": rule}

        case = {
            "id": f"ceval_{item.get('id', role)}_{len(cases)}",
            "source": f"CharacterEval (2024) — {role} ({mbti})",
            "character_state": {
                "name": role,
                "personality": {
                    **personality,
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
                "description": event_desc,
                "type": "social",
                "participants": [],
                "significance": 0.5,
                "tags": ["dialogue", "character_eval"],
            },
            "expected": expected,
            "_mbti": mbti,
            "_novel": item.get("novel_name", ""),
        }
        cases.append(case)

    return cases


if __name__ == "__main__":
    cases = extract_cases()
    print(f"Extracted {len(cases)} cases from CharacterEval")

    # MBTI 分布
    mbti_counts = {}
    for c in cases:
        m = c.get("_mbti", "?")
        mbti_counts[m] = mbti_counts.get(m, 0) + 1
    print(f"MBTI distribution: {len(mbti_counts)} types")
    for m, n in sorted(mbti_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {m}: {n}")

    out_path = OUTPUT_DIR / "character_eval_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")
