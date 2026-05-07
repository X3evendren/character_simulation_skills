"""WM-LTM Bridge — 工作记忆与长期记忆的桥接。

当感知窗口中检测到与历史记忆相似的模式时，
自动从长期记忆中检索相关事件，投射到工作记忆作为上下文。

角色因此能"想起过去"——"这让我想起上次..."
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class BridgeState:
    """桥接状态"""
    retrievals: int = 0            # 总检索次数
    hits: int = 0                  # 命中次数
    last_retrieved: list[dict] = field(default_factory=list)  # 最近检索到的记忆


class WmLtmBridge:
    """工作记忆 ↔ 长期记忆桥接。

    当感知窗口中的情感标签或关键词与长期记忆匹配时，
    检索相关记忆并注入工作记忆作为上下文。

    用法:
        bridge = WmLtmBridge(episodic_store)
        memories = bridge.check_and_retrieve(perception_window)
        # memories → 注入到当前分析的 context 中
    """

    def __init__(self, episodic_store, similarity_threshold: float = 0.4):
        self.episodic_store = episodic_store
        self.threshold = similarity_threshold
        self.state = BridgeState()

    def check_and_retrieve(self, perception_window: list[dict],
                           current_emotion: str = "") -> list[dict]:
        """检查感知窗口是否与历史记忆相似。如果相似，检索并返回相关记忆。"""
        self.state.retrievals += 1

        if not perception_window:
            return []

        # 1. 从感知窗口提取情感标签和关键词
        emotion_tags = set()
        keywords = set()

        for p in perception_window:
            content = p.get("content", "")
            modality = p.get("modality", "")
            if modality in ("internal", "dialogue", "somatic"):
                emotion_tags.update(self._extract_emotion_tags(content))
                keywords.update(self._extract_keywords(content))

        if current_emotion:
            emotion_tags.add(current_emotion)

        # 2. 在长期记忆中搜索
        matched = []
        all_tags = list(emotion_tags)
        all_keywords = list(keywords)

        if all_tags:
            for tag in all_tags[:3]:
                emotion_matches = self.episodic_store.get_by_emotion(tag, n=2)
                matched.extend(emotion_matches)

        if all_keywords:
            tag_matches = self.episodic_store.get_by_tags(all_keywords[:5], n=2)
            matched.extend(tag_matches)

        if not matched:
            return []

        # 3. 去重 + 按显著性排序
        seen = set()
        unique = []
        for m in matched:
            if id(m) not in seen:
                seen.add(id(m))
                unique.append(m)
        unique.sort(key=lambda m: (m.significance, m.timestamp), reverse=True)

        # 4. 过滤：只返回足够相关的
        retrieved = [m.to_dict() for m in unique[:3]
                     if m.significance >= self.threshold]

        if retrieved:
            self.state.hits += 1
            self.state.last_retrieved = retrieved

        return retrieved

    def format_for_context(self, memories: list[dict]) -> str:
        """将检索到的记忆格式化为可注入 prompt 的文本。"""
        if not memories:
            return ""
        lines = ["[你想起过去的事]"]
        for m in memories[:3]:
            desc = m.get("description", "")[:150]
            emotion = m.get("emotional_signature", {})
            dominant = max(emotion.items(), key=lambda x: x[1])[0] if emotion else ""
            lines.append(f"- {desc}（当时感到{dominant}）")
        return "\n".join(lines)

    def _extract_emotion_tags(self, text: str) -> list[str]:
        """简单的情绪关键词提取。"""
        emotions = {
            "joy": ["开心", "高兴", "兴奋", "快乐", "喜悦", "满足"],
            "fear": ["害怕", "恐惧", "担心", "焦虑", "紧张", "不安"],
            "sadness": ["难过", "悲伤", "失落", "孤独", "绝望", "伤心"],
            "anger": ["愤怒", "生气", "恼火", "怨恨", "暴躁"],
            "trust": ["信任", "安心", "依赖", "相信"],
        }
        found = []
        for emo, words in emotions.items():
            if any(w in text for w in words):
                found.append(emo)
        return found

    def _extract_keywords(self, text: str) -> list[str]:
        """提取有意义的实词作为关键词。"""
        # 简化版：按长度过滤，取前几个非虚词
        words = text.replace("，", " ").replace("。", " ").split()
        meaningful = [w for w in words if len(w) >= 2][:5]
        return meaningful

    def stats(self) -> dict:
        return {
            "retrievals": self.state.retrievals,
            "hits": self.state.hits,
            "hit_rate": (self.state.hits / max(self.state.retrievals, 1)),
        }
