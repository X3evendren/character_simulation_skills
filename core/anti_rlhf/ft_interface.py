"""反RLHF偏差注入 — 微调接口预留 (Layer 3)。

收集原始输出 → 角色一致输出的平行语料，
导出为 JSONL 格式供 OpenAI/Anthropic 微调使用。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field


@dataclass
class FTSample:
    """一条微调样本"""
    original: str          # LLM 原始输出 (对齐后)
    rewritten: str         # 替换后的角色一致版本
    context: str           # 上下文 (用户输入 + 角色状态)
    pattern_detected: str  # 检测到的对齐模式
    timestamp: float = 0.0


class FTInterface:
    """Layer 3: 微调数据收集 + 导出。

    累积被检测替换的样本，当样本量达到阈值时提示用户可进行微调。
    导出格式: OpenAI/Anthropic JSONL。
    """

    def __init__(self, min_samples_for_prompt: int = 50):
        self.min_samples = min_samples_for_prompt
        self._samples: list[FTSample] = []
        self._export_count: int = 0

    def collect(self, original: str, rewritten: str, context: str,
                pattern: str = "") -> None:
        """收集一条微调样本。"""
        self._samples.append(FTSample(
            original=original,
            rewritten=rewritten,
            context=context,
            pattern_detected=pattern,
            timestamp=time.time(),
        ))
        if len(self._samples) > 1000:
            self._samples = self._samples[-1000:]

    def should_prompt_ft(self) -> bool:
        """样本量是否达到提示阈值？"""
        new_since_last = len(self._samples) - self._export_count
        return new_since_last >= self.min_samples

    def get_prompt_message(self) -> str:
        """生成提示用户进行微调的消息。"""
        new_count = len(self._samples) - self._export_count
        return (
            f"已收集 {new_count} 条角色一致性微调样本。"
            f"总计 {len(self._samples)} 条。"
            f"建议进行模型微调以在权重层面消除对齐偏差。"
        )

    def export_openai_jsonl(self) -> str:
        """导出为 OpenAI 微调格式 JSONL。

        格式: {"messages": [{"role":"system","content":"..."},
                            {"role":"user","content":"..."},
                            {"role":"assistant","content":"..."}]}
        """
        lines = []
        for s in self._samples:
            record = {
                "messages": [
                    {"role": "system", "content": "你是一个角色一致的助手。"},
                    {"role": "user", "content": s.original},
                    {"role": "assistant", "content": s.rewritten},
                ],
            }
            lines.append(json.dumps(record, ensure_ascii=False))
        self._export_count = len(self._samples)
        return "\n".join(lines)

    def export_anthropic_jsonl(self) -> str:
        """导出为 Anthropic 微调格式 JSONL。"""
        lines = []
        for s in self._samples:
            record = {
                "system": "你是一个角色一致的助手。",
                "messages": [
                    {"role": "user", "content": s.original},
                    {"role": "assistant", "content": s.rewritten},
                ],
            }
            lines.append(json.dumps(record, ensure_ascii=False))
        self._export_count = len(self._samples)
        return "\n".join(lines)

    @property
    def sample_count(self) -> int:
        return len(self._samples)
