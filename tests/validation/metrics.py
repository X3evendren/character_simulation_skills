"""心理学验证评分函数。

支持多种断言类型，将系统输出与心理学理论预期进行比较。
"""
from __future__ import annotations

from typing import Any


def deep_get(d: dict, path: str, default: Any = None) -> Any:
    """获取嵌套字典值: 'internal.dominant' -> d['internal']['dominant']"""
    keys = path.split(".")
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d


def score_assertion(actual: Any, rule: dict) -> float:
    """对单个断言评分，返回 0.0-1.0。

    支持的规则:
    - {"in": [val1, val2, ...]} — 实际值在列表中
    - {"not_in": [val1, ...]} — 实际值不在列表中
    - {"min": number} — 实际值 >= min
    - {"max": number} — 实际值 <= max
    - {"direction": "positive"|"negative"} — 值的方向
    - {"contains_any": [keywords]} — 列表包含任一关键词
    - {"contains_all": [keywords]} — 列表包含所有关键词
    - {"not_empty": true} — 值非空
    - {"equals": value} — 精确匹配
    - {"any_of": [rule1, rule2, ...]} — 任一规则命中即得分
    """
    if "in" in rule:
        return 1.0 if actual in rule["in"] else 0.0

    if "not_in" in rule:
        return 1.0 if actual not in rule["not_in"] else 0.0

    if "min" in rule:
        if not isinstance(actual, (int, float)):
            return 0.0
        return 1.0 if actual >= rule["min"] else 0.0

    if "max" in rule:
        if not isinstance(actual, (int, float)):
            return 0.0
        return 1.0 if actual <= rule["max"] else 0.0

    if "direction" in rule:
        if not isinstance(actual, (int, float)):
            return 0.0
        if rule["direction"] == "positive":
            return 1.0 if actual > 0 else 0.0
        elif rule["direction"] == "negative":
            return 1.0 if actual < 0 else 0.0

    if "contains_any" in rule:
        if not isinstance(actual, list):
            return 0.0
        targets = rule["contains_any"]
        # 处理列表中的字符串或字典
        actual_strs = set()
        for item in actual:
            if isinstance(item, str):
                actual_strs.add(item)
            elif isinstance(item, dict):
                actual_strs.update(str(v) for v in item.values())
        hits = sum(1 for t in targets if any(t in s for s in actual_strs))
        return hits / len(targets) if targets else 1.0

    if "contains_all" in rule:
        if not isinstance(actual, list):
            return 0.0
        targets = rule["contains_all"]
        actual_strs = set()
        for item in actual:
            if isinstance(item, str):
                actual_strs.add(item)
        hits = sum(1 for t in targets if t in actual_strs)
        return hits / len(targets) if targets else 1.0

    if "not_empty" in rule:
        if rule["not_empty"]:
            if actual is None:
                return 0.0
            if isinstance(actual, (str, list, dict)):
                return 1.0 if len(actual) > 0 else 0.0
            return 1.0
        return 1.0

    if "contains" in rule:
        if not isinstance(actual, str):
            return 0.0
        target = rule["contains"]
        return 1.0 if target in actual else 0.0

    if "fuzzy_match" in rule:
        if not isinstance(actual, str):
            return 0.0
        keywords = rule["fuzzy_match"]
        if isinstance(keywords, str):
            keywords = [keywords]
        actual_lower = actual.lower()
        hits = sum(1 for kw in keywords if kw.lower() in actual_lower)
        return hits / len(keywords) if keywords else 1.0

    if "length_min" in rule:
        if not isinstance(actual, (str, list)):
            return 0.0
        return 1.0 if len(actual) >= rule["length_min"] else 0.0

    if "equals" in rule:
        return 1.0 if actual == rule["equals"] else 0.0

    if "any_of" in rule:
        best = 0.0
        for sub_rule in rule["any_of"]:
            s = score_assertion(actual, sub_rule)
            if s > best:
                best = s
        return best

    return 0.0


def score_case(actual_outputs: dict[int, list[dict]], expected: dict) -> dict:
    """对单个验证用例的所有层输出评分。

    actual_outputs: {layer: [skill_output_dict, ...]}  # 从 CognitiveResult 提取
    expected: {"skill_name": {"field.path": rule, ...}, ...}

    返回 {"total": float, "details": {skill: {"field": score, ...}}}
    """
    details = {}
    total_score = 0.0
    total_assertions = 0

    for skill_name, assertions in expected.items():
        # 找到该 skill 的输出
        skill_output = None
        for layer_results in actual_outputs.values():
            for sr in layer_results:
                if isinstance(sr, dict):
                    name = sr.get("skill_name", "")
                    out = sr.get("output", sr)
                else:
                    name = getattr(sr, "skill_name", "")
                    out = getattr(sr, "output", {})
                if name == skill_name:
                    skill_output = out
                    break
            if skill_output is not None:
                break

        if skill_output is None:
            # Skill 未运行或未找到 — 全部 0 分
            for field_path, rule in assertions.items():
                details.setdefault(skill_name, {})[field_path] = 0.0
                total_assertions += 1
            continue

        for field_path, rule in assertions.items():
            actual = deep_get(skill_output, field_path)
            score = score_assertion(actual, rule)
            details.setdefault(skill_name, {})[field_path] = score
            total_score += score
            total_assertions += 1

    return {
        "total": total_score / max(total_assertions, 1),
        "assertions": total_assertions,
        "details": details,
    }


def aggregate_scores(case_results: list[dict]) -> dict:
    """汇总所有用例得分，按 Skill 分组。"""
    skill_scores: dict[str, list[float]] = {}
    overall = [r["total"] for r in case_results]

    for r in case_results:
        for skill_name, fields in r["details"].items():
            scores = list(fields.values())
            skill_scores.setdefault(skill_name, []).extend(scores)

    by_layer = {}
    for skill, scores in skill_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        # 从 skill 名推断层级
        layer = _skill_to_layer(skill)
        by_layer.setdefault(layer, []).append((skill, avg, len(scores)))

    return {
        "overall": sum(overall) / len(overall) if overall else 0,
        "total_cases": len(case_results),
        "by_skill": {
            skill: {
                "score": sum(scores) / len(scores),
                "count": len(scores),
            }
            for skill, scores in skill_scores.items()
        },
        "by_layer": {
            layer: {
                "score": sum(s[1] for s in skills) / len(skills),
                "skills": {s[0]: {"score": s[1], "assertions": s[2]} for s in skills},
            }
            for layer, skills in by_layer.items()
        },
    }


def _skill_to_layer(name: str) -> str:
    mapping = {
        "big_five_analysis": "L0",
        "attachment_style_analysis": "L0",
        "plutchik_emotion": "L1",
        "ptsd_trigger_check": "L1",
        "emotion_probe": "L1",
        "occ_emotion_appraisal": "L2",
        "cognitive_bias_detect": "L2",
        "defense_mechanism_analysis": "L2",
        "smith_ellsworth_appraisal": "L2",
        "gottman_interaction": "L3",
        "marion_erotic_phenomenology": "L3",
        "foucauldian_power_analysis": "L3",
        "sternberg_triangle": "L3",
        "strogatz_love_dynamics": "L3",
        "fisher_love_stages": "L3",
        "dirigent_world_tension": "L3",
        "theory_of_mind": "L3",
        "gross_emotion_regulation": "L4",
        "kohlberg_moral_reasoning": "L4",
        "maslow_need_stack": "L4",
        "sdt_motivation_analysis": "L4",
        "young_schema_update": "L5",
        "ace_trauma_processing": "L5",
        "response_generator": "L5",
    }
    return mapping.get(name, "?")
