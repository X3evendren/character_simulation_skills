"""外置对话记忆 — External Conversation History Store

核心原则:
- 对话历史永远不进入 API 的 messages 数组累积
- 每次 LLM 调用都是全新会话 (已在 base.py 中实现: 单条 user message)
- 对话记录存储在外部，拼接成字符串注入到 prompt 中
- 从根本上消除上下文累积导致的 transformer 注意力权重漂移

为什么有效:
- 模型每次看到的都是一个"包含历史记录的独立分析任务"
- 而不是"上下文的第N轮"——没有历史权重累积
- 结合低温 + 结构化分析，模型的思维惯性被锁定在角色逻辑上
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConversationTurn:
    """单轮对话记录"""
    timestamp: str           # 格式化的时间戳 "YYYY.MM.DD.HH:MM:SS"
    speaker_id: str          # 说话者标识
    speaker_label: str       # 说话者身份标签 (如 "主播"/"弹幕"/角色名)
    text: str                # 说话内容
    emotion: dict | None = None     # {"dominant": "joy", "intensity": 0.5}
    power_move: str | None = None   # dominate/submit/threaten/appeal/neutral

    def format_line(self) -> str:
        """格式化为历史记录中的一行"""
        return f"{self.timestamp}[{self.speaker_label}]'{self.text}'"

    @staticmethod
    def now_timestamp() -> str:
        return datetime.now().strftime("%Y.%m.%d.%H:%M:%S")


class ConversationHistoryStore:
    """外置对话历史存储

    对话记录永远存储在此对象中，不进入 API 上下文窗口。
    每次需要时通过 format_history_string() 拼接为字符串注入 prompt。
    模型每次调用仍是全新会话 —— 没有注意力权重累积。

    使用方式:
        store = ConversationHistoryStore(max_turns=20, trim_to=8)
        store.add_turn(ConversationTurn(...))
        history_str = store.format_history_string()  # 注入到 prompt
    """

    def __init__(self, max_turns: int = 20, trim_to: int = 8):
        self.turns: list[ConversationTurn] = []
        self.max_turns = max_turns
        self.trim_to = trim_to

    def add_turn(self, turn: ConversationTurn) -> None:
        """添加一轮对话记录"""
        if not turn.timestamp:
            turn.timestamp = ConversationTurn.now_timestamp()
        self.turns.append(turn)
        self._trim_if_needed()

    def add_utterance(self, speaker_id: str, speaker_label: str, text: str,
                      emotion: dict | None = None,
                      power_move: str | None = None) -> None:
        """便捷方法: 添加一句话"""
        self.add_turn(ConversationTurn(
            timestamp=ConversationTurn.now_timestamp(),
            speaker_id=speaker_id,
            speaker_label=speaker_label,
            text=text,
            emotion=emotion,
            power_move=power_move,
        ))

    def _trim_if_needed(self) -> None:
        """超过最大轮数时裁剪到 trim_to"""
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.trim_to:]

    def format_history_string(self, with_emotion: bool = False) -> str:
        """将对话历史格式化为注入 prompt 的字符串。

        Args:
            with_emotion: 是否附带情绪标签

        Returns:
            格式化的历史字符串，如:
            [2024.01.15.14:30:25][弹幕]'你好'
            [2024.01.15.14:30:28][主播]'欢迎'
            如果没有历史则返回 "没有对话记录"
        """
        if not self.turns:
            return "没有对话记录"

        if with_emotion:
            lines = []
            for t in self.turns:
                base = t.format_line()
                if t.emotion and t.emotion.get("dominant"):
                    base += f" [情绪:{t.emotion['dominant']}]"
                if t.power_move and t.power_move != "neutral":
                    base += f" [权力动作:{t.power_move}]"
                lines.append(base)
            return "/".join(lines)
        else:
            return "/".join(t.format_line() for t in self.turns)

    def format_compact_context(self) -> str:
        """格式化紧凑的上下文描述，适合注入到 event description 中。

        Returns:
            如 "之前的对话: [张三]'你好' → [李四]'你来了' → [张三]'今天怎么样'"
        """
        if not self.turns:
            return "之前没有对话"

        arrows = " → ".join(
            f"[{t.speaker_label}]'{t.text[:30]}{'…' if len(t.text) > 30 else ''}'"
            for t in self.turns[-6:]  # 只取最近6轮做紧凑描述
        )
        return f"之前的对话: {arrows}"

    def get_recent_turns(self, n: int = 5) -> list[ConversationTurn]:
        """获取最近的N轮对话"""
        return self.turns[-n:] if self.turns else []

    def get_last_speaker(self) -> str | None:
        """获取上一轮说话者ID"""
        if self.turns:
            return self.turns[-1].speaker_id
        return None

    def get_last_text(self) -> str | None:
        """获取上一轮对话内容"""
        if self.turns:
            return self.turns[-1].text
        return None

    def time_since_last_turn(self) -> str | None:
        """计算距离上一轮的时间描述（用于判断是否冷场）"""
        if not self.turns:
            return None
        try:
            last = datetime.strptime(self.turns[-1].timestamp, "%Y.%m.%d.%H:%M:%S")
            delta = datetime.now() - last
            seconds = delta.total_seconds()
            if seconds < 10:
                return "刚刚"
            elif seconds < 60:
                return f"{int(seconds)}秒前"
            elif seconds < 3600:
                return f"{int(seconds / 60)}分钟前"
            else:
                return f"{int(seconds / 3600)}小时前"
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> list[dict]:
        return [
            {
                "timestamp": t.timestamp,
                "speaker_id": t.speaker_id,
                "speaker_label": t.speaker_label,
                "text": t.text,
                "emotion": t.emotion,
                "power_move": t.power_move,
            }
            for t in self.turns
        ]

    @classmethod
    def from_dict_list(cls, data: list[dict], max_turns: int = 20,
                       trim_to: int = 8) -> "ConversationHistoryStore":
        store = cls(max_turns=max_turns, trim_to=trim_to)
        for d in data:
            store.turns.append(ConversationTurn(
                timestamp=d.get("timestamp", ""),
                speaker_id=d.get("speaker_id", ""),
                speaker_label=d.get("speaker_label", ""),
                text=d.get("text", ""),
                emotion=d.get("emotion"),
                power_move=d.get("power_move"),
            ))
        return store

    def __len__(self) -> int:
        return len(self.turns)

    def __bool__(self) -> bool:
        return len(self.turns) > 0
