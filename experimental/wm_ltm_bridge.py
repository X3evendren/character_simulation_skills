"""WM-LTM Bridge — 工作记忆与长期记忆的桥接。

当感知窗口中检测到与历史记忆相似的模式时，
自动从长期记忆中检索相关事件，投射到工作记忆作为上下文。

角色因此能"想起过去"——"这让我想起上次..."
"""
from __future__ import annotations

import time
import math
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

        # 4. 情感签名余弦相似度过滤
        # 从感知窗口构建当前情感向量
        current_emotion_vec = {}
        if current_emotion:
            current_emotion_vec[current_emotion] = 0.7
        for tag in emotion_tags:
            if tag not in current_emotion_vec:
                current_emotion_vec[tag] = 0.3

        filtered = []
        for m in unique[:6]:
            mem_emo = m.emotional_signature
            sim = self._cosine_similarity(current_emotion_vec, mem_emo)
            if sim >= 0.15 or m.significance >= 0.6:
                filtered.append((sim, m))

        # 按相似度+显著性排序
        filtered.sort(key=lambda x: x[0] * 0.4 + x[1].significance * 0.6, reverse=True)
        retrieved = [m.to_dict() for _, m in filtered[:3]]

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
        """从情感词典做子串匹配提取情绪标签。"""
        tags = set()
        for word in self._get_emotion_words():
            if word in text:
                for basic, fines in self._get_emotion_map().items():
                    if word in fines:
                        tags.add(basic)
                        break
        return list(tags)

    def _extract_keywords(self, text: str) -> list[str]:
        """2-4字滑动窗口提取实词，过滤虚词和标点。"""
        stop_chars = set("，。！？、；：""''（）…— \t\n\r,./;'[]<>?!@#$")
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就",
                      "不", "人", "都", "一", "一个", "这个", "那个",
                      "什么", "怎么", "为什么", "因为", "所以", "但是",
                      "可以", "没有", "这个", "这里", "那里", "已经"}
        # 清理标点
        cleaned = "".join(c for c in text if c not in stop_chars)
        # 2-4字滑动窗口
        keywords = set()
        for size in (4, 3, 2):
            for i in range(len(cleaned) - size + 1):
                chunk = cleaned[i:i+size]
                if chunk not in stop_words:
                    keywords.add(chunk)
        # 长词优先，去子串重复
        result = []
        for kw in sorted(keywords, key=len, reverse=True):
            if not any(kw in r for r in result):
                result.append(kw)
            if len(result) >= 8:
                break
        return result

    @staticmethod
    def _get_emotion_words() -> list[str]:
        """延迟获取所有细粒度情绪词。"""
        try:
            from character_mind.core.emotion_vocabulary import ALL_FINE_GRAINED
            return ALL_FINE_GRAINED
        except ImportError:
            # fallback: 常用情绪词
            return [
                "焦虑", "恐慌", "不安", "畏惧", "绝望", "心碎", "沮丧",
                "愤怒", "暴怒", "怨恨", "嫉妒", "敌意",
                "狂喜", "满足", "自豪", "依恋", "感激",
                "反感", "鄙夷", "憎恶", "震惊", "困惑",
            ]

    @staticmethod
    def _get_emotion_map() -> dict[str, list[str]]:
        """延迟获取基础情绪→细粒度映射。"""
        try:
            from character_mind.core.emotion_vocabulary import FINE_GRAINED_EMOTIONS
            return FINE_GRAINED_EMOTIONS
        except ImportError:
            return {
                "fear": ["焦虑", "恐慌", "不安", "畏惧", "紧张"],
                "sadness": ["失落", "沮丧", "绝望", "心碎", "孤独"],
                "anger": ["愤怒", "暴怒", "怨恨", "嫉妒", "暴躁"],
                "joy": ["狂喜", "满足", "自豪", "欣慰", "雀跃"],
                "disgust": ["反感", "鄙夷", "憎恶", "恶心", "嫌弃"],
            }

    @staticmethod
    def _cosine_similarity(vec1: dict, vec2: dict) -> float:
        """两个情感向量的余弦相似度。"""
        if not vec1 or not vec2:
            return 0.0
        keys = set(vec1) | set(vec2)
        dot = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in keys)
        norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v**2 for v in vec2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def stats(self) -> dict:
        return {
            "retrievals": self.state.retrievals,
            "hits": self.state.hits,
            "hit_rate": (self.state.hits / max(self.state.retrievals, 1)),
        }
