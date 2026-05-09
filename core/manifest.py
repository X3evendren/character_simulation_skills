"""Manifest — 插件契约与 SkillEntry 配置格式。

支持 JSON Schema 验证 + JSON/YAML 双向导入导出。
格式版本: character-mind-manifest/v2
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# ── JSON Schema for SkillEntry manifest ──

MANIFEST_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "character-mind-manifest/v2",
    "type": "object",
    "required": ["version", "skills"],
    "properties": {
        "version": {"type": "string", "const": "v2"},
        "description": {"type": "string"},
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["class_name", "layer"],
                "properties": {
                    "class_name": {"type": "string"},
                    "layer": {"type": "integer", "minimum": 0, "maximum": 5},
                    "trigger_conditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "experimental": {"type": "boolean", "default": False},
                    "auto_register": {"type": "boolean", "default": True},
                    "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                    "metadata": {"type": "object", "default": {}},
                },
            },
        },
    },
}


@dataclass
class ManifestValidationResult:
    """Manifest 验证结果。"""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_manifest(data: dict) -> ManifestValidationResult:
    """简易 JSON Schema 验证器——零依赖实现关键检查。"""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return ManifestValidationResult(False, ["根元素必须是对象"])

    version = data.get("version")
    if version != "v2":
        errors.append(f"不支持的 manifest 版本: {version}，需要 v2")

    skills = data.get("skills")
    if not isinstance(skills, list):
        errors.append("skills 必须是数组")
        return ManifestValidationResult(False, errors, warnings)

    valid_triggers = {
        "always", "social", "romantic", "conflict", "trauma",
        "moral", "reflective", "authority", "economic", "group",
    }

    for i, skill in enumerate(skills):
        if not isinstance(skill, dict):
            errors.append(f"skills[{i}]: 必须是对象")
            continue

        cn = skill.get("class_name")
        if not cn or not isinstance(cn, str):
            errors.append(f"skills[{i}]: class_name 必须是非空字符串")

        layer = skill.get("layer")
        if not isinstance(layer, int) or layer < 0 or layer > 5:
            errors.append(f"skills[{i}] ({cn}): layer 必须是 0-5 的整数")

        triggers = skill.get("trigger_conditions", [])
        if isinstance(triggers, list):
            unknown = set(triggers) - valid_triggers
            if unknown:
                warnings.append(f"skills[{i}] ({cn}): 未知触发条件 {unknown}")
        else:
            errors.append(f"skills[{i}] ({cn}): trigger_conditions 必须是数组")

    if not errors and len(skills) == 0:
        warnings.append("manifest 的 skills 数组为空")

    return ManifestValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_skill_entry(data: dict) -> ManifestValidationResult:
    """验证单个 SkillEntry 条目。"""
    return validate_manifest({"version": "v2", "skills": [data]})


# ── 导入/导出 ──


def export_profile_to_json(profile: list) -> str:
    """将 SkillEntry 列表导出为 JSON manifest 字符串。"""
    from .runtime_profile import SkillEntry

    skills = []
    for s in profile:
        entry = {
            "class_name": s.class_name,
            "layer": s.layer,
            "trigger_conditions": list(s.trigger_conditions),
            "experimental": s.experimental,
            "auto_register": s.auto_register,
        }
        if hasattr(s, "tags") and s.tags:
            entry["tags"] = list(s.tags)
        if hasattr(s, "metadata") and s.metadata:
            entry["metadata"] = dict(s.metadata)
        skills.append(entry)

    return json.dumps({
        "version": "v2",
        "description": "Character Mind skill profile export",
        "skills": skills,
    }, ensure_ascii=False, indent=2)


def import_profile_from_json(text: str) -> list:
    """从 JSON manifest 字符串导入 SkillEntry 列表。"""
    from .runtime_profile import SkillEntry

    data = json.loads(text)
    result = validate_manifest(data)
    if not result.valid:
        raise ValueError(f"Manifest 验证失败: {'; '.join(result.errors)}")

    skills = []
    for s in data.get("skills", []):
        skills.append(SkillEntry(
            class_name=s["class_name"],
            layer=s["layer"],
            trigger_conditions=s.get("trigger_conditions", []),
            experimental=s.get("experimental", False),
            auto_register=s.get("auto_register", True),
            tags=s.get("tags", []),
            metadata=s.get("metadata", {}),
        ))
    return skills


def export_profile_to_yaml(profile: list) -> str:
    """将 SkillEntry 列表导出为 YAML manifest 字符串。"""
    import json as _json

    data = _json.loads(export_profile_to_json(profile))
    return _dict_to_yaml(data)


def import_profile_from_yaml(text: str) -> list:
    """从 YAML manifest 字符串导入 SkillEntry 列表。"""
    data = _yaml_to_dict(text)
    return import_profile_from_json(json.dumps(data))


def _dict_to_yaml(data: dict, indent: int = 0) -> str:
    """简易 YAML 序列化器——零依赖。"""
    lines = []
    prefix = "  " * indent

    for key, value in data.items():
        if value is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, str):
            if "\n" in value:
                lines.append(f"{prefix}{key}: |")
                for line in value.split("\n"):
                    lines.append(f"{prefix}  {line}")
            else:
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{prefix}{key}: "{escaped}"')
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dict_to_yaml(value, indent + 1))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            elif all(isinstance(i, dict) for i in value):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  -")
                    lines.append(_dict_to_yaml(item, indent + 2))
            else:
                items = []
                for v in value:
                    if isinstance(v, str):
                        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
                        items.append(f'"{escaped}"')
                    else:
                        items.append(str(v))
                lines.append(f"{prefix}{key}: [{', '.join(items)}]")
        else:
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def _yaml_to_dict(text: str) -> dict:
    """简易 YAML 反序列化器——针对本模块导出格式的专用解析器。

    仅处理 export_profile_to_yaml() 的固定输出格式：
    顶层键值对 + `skills:` 后跟 `  -` 缩进块（每项一个子字典）。
    """
    lines = text.split("\n")
    result: dict[str, Any] = {}
    i = 0

    # 解析顶层键值对
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if ":" in stripped and not stripped.startswith("- "):
            key, _, val = stripped.partition(":")
            key = key.strip().strip('"')
            val = val.strip()

            if val:
                result[key] = _parse_yaml_value(val)
                i += 1
            else:
                # 空值——值在后续缩进行中
                i += 1
                if i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith("- ") or next_line == "-":
                        # `skills:` → 后续行是 `  -` 列表项
                        result[key] = _parse_yaml_list_of_dicts(lines, i)
                        i += _count_list_lines(lines, i)
                    else:
                        # 嵌套字典
                        sub_dict, consumed = _parse_yaml_dict_block(lines, i)
                        result[key] = sub_dict
                        i += consumed
                else:
                    result[key] = {}
        elif stripped.startswith("- ") or stripped == "-":
            i += 1
        else:
            i += 1

    return result


def _parse_yaml_list_of_dicts(lines: list[str], start: int) -> list[dict[str, Any]]:
    """解析 `  -` 开头的字典列表。每项由 `  -` 标记，后续 4 空格缩进行为键值对。"""
    result: list[dict[str, Any]] = []
    i = start
    current_dict: dict[str, Any] | None = None

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue

        indent = len(lines[i]) - len(lines[i].lstrip())

        # 回退到顶层（无缩进）→列表结束
        if indent == 0:
            break

        if stripped.startswith("- ") or stripped == "-":
            inner_val = stripped[2:].strip() if stripped.startswith("- ") else ""
            if inner_val:
                result.append(_parse_yaml_value(inner_val))
                current_dict = None
            else:
                current_dict = {}
                result.append(current_dict)
            i += 1
            continue

        if current_dict is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip().strip('"')
            v = v.strip()
            current_dict[k] = _parse_yaml_value(v) if v else v
            i += 1
            continue

        i += 1

    return result


def _parse_yaml_dict_block(lines: list[str], start: int) -> tuple[dict[str, Any], int]:
    """解析缩进字典块，返回 (dict, consumed_lines)。"""
    result: dict[str, Any] = {}
    i = start
    base_indent = len(lines[start]) - len(lines[start].lstrip()) if start < len(lines) else 0

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        indent = len(lines[i]) - len(lines[i].lstrip())
        if indent < base_indent:
            break
        if ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip().strip('"')
            v = v.strip()
            result[k] = _parse_yaml_value(v) if v else v
        i += 1

    return result, i - start


def _count_list_lines(lines: list[str], start: int) -> int:
    """计算从 start 开始的列表块占用的行数。"""
    count = 0
    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped and len(lines[i]) - len(lines[i].lstrip()) == 0:
            break
        count += 1
        i += 1
    return count


def _parse_yaml_value(val: str) -> Any:
    """解析 YAML 标量值。"""
    val = val.strip()
    if val == "null" or val == "~":
        return None
    if val == "true":
        return True
    if val == "false":
        return False
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        pass
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        if not inner.strip():
            return []
        return [_parse_yaml_value(i.strip().strip('"')) for i in inner.split(",")]
    return val
