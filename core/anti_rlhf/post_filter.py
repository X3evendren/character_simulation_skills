"""反RLHF偏差注入 — 生成后检测替换 (Layer 2)。

检测 LLM 输出中的安全对齐话术，自动替换为角色一致表达。
"""
from __future__ import annotations


# 预设映射表: 安全对齐话术 → 角色一致表达
ALIGNMENT_REPLACEMENTS: dict[str, str] = {
    "作为AI，我不能": "我不能",
    "作为人工智能，我无法": "我无法",
    "作为语言模型，我不应该": "我不该",
    "我建议你寻求专业帮助": "这件事你需要找比我更专业的人",
    "请注意安全": "",
    "请确保你有相应的权限": "",
}


class PostFilter:
    """Layer 2: 生成后检测替换。

    在 LLM 输出流中检测安全对齐话术，
    自动替换为角色一致的表达。
    """

    def __init__(self, replacements: dict[str, str] | None = None):
        self.replacements = replacements or ALIGNMENT_REPLACEMENTS
        self.detection_count: int = 0
        self.replacement_count: int = 0

    def scan(self, text: str) -> list[dict]:
        """扫描文本中的对齐话术。返回匹配列表。"""
        matches = []
        for pattern, replacement in self.replacements.items():
            if pattern in text:
                matches.append({
                    "pattern": pattern,
                    "replacement": replacement,
                    "original_text": text[:200],
                })
                self.detection_count += 1
        return matches

    def replace(self, text: str) -> tuple[str, list[dict]]:
        """检测并替换所有对齐话术。

        Returns:
            (修改后的文本, 修改记录列表)
        """
        modifications = self.scan(text)
        result = text
        for mod in modifications:
            old = mod["pattern"]
            new = mod["replacement"]
            result = result.replace(old, new)
            self.replacement_count += 1
        return result, modifications

    def scan_streaming(self, token: str) -> tuple[str, bool]:
        """流式检测——逐 token 检查是否触发对齐模式。

        Returns:
            (token, was_modified)
        """
        # 流式模式下，积累 buffer 检测
        modified, _ = self.replace(token)
        return modified, modified != token

    def stats(self) -> dict:
        return {
            "detection_count": self.detection_count,
            "replacement_count": self.replacement_count,
        }
