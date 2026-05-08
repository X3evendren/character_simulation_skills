"""Blackboard — TOCA 连续状态流的核心共享状态。

版本化字段 + 乐观锁 + 异步安全读写。
所有管道实例通过 Blackboard 共享心理状态，不直接通信。

字段级版本控制: 每个字段独立版本号，实例写入时自增。
乐观锁: 读取时记录版本，写入时检查冲突，旧版本写入被拒绝。
"""
from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldMeta:
    """字段元数据"""
    value: Any
    version: int = 0
    updated_at: float = 0.0
    updated_by: int = 0  # 实例 ID

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "version": self.version,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


class Blackboard:
    """版本化共享状态黑板。

    用法:
        bb = Blackboard()
        bb.write("pad", {"pleasure": -0.2, "arousal": 0.5}, instance_id=3)
        snapshot = bb.read(["pad", "dominant_emotion"])
        pad_version = bb.get_version("pad")

    乐观写入:
        success = bb.try_write("pad", new_value, expected_version=5, instance_id=3)
        # 如果 version != 5（已被别人修改），返回 False
    """

    def __init__(self):
        self._fields: dict[str, FieldMeta] = {}
        self._lock = asyncio.Lock()
        self._event_log: list[dict] = []  # 变更日志（用于调试/回放）
        self.created_at = time.time()

    # ═══ 基础读写 ═══

    def write(self, key: str, value: Any, instance_id: int = 0):
        """直接写入（覆盖）。自动递增版本号。"""
        if key in self._fields:
            meta = self._fields[key]
            meta.value = value
            meta.version += 1
            meta.updated_at = time.time()
            meta.updated_by = instance_id
        else:
            self._fields[key] = FieldMeta(
                value=value, version=1,
                updated_at=time.time(), updated_by=instance_id,
            )
        # 事件日志
        self._event_log.append({
            "t": time.time(),
            "key": key,
            "value": value,
            "version": self._fields[key].version,
            "instance_id": instance_id,
        })
        if len(self._event_log) > 500:
            self._event_log = self._event_log[-500:]

    def read(self, keys: list[str] | None = None) -> dict:
        """读取指定字段的最新值。keys=None 时读取全部。"""
        if keys is None:
            keys = list(self._fields.keys())
        return {k: self._fields[k].value for k in keys if k in self._fields}

    def read_with_versions(self, keys: list[str] | None = None) -> dict[str, tuple[Any, int]]:
        """读取并返回 (值, 版本号)。用于乐观锁。"""
        if keys is None:
            keys = list(self._fields.keys())
        return {k: (self._fields[k].value, self._fields[k].version)
                for k in keys if k in self._fields}

    # ═══ 乐观并发 ═══

    def try_write(self, key: str, value: Any, expected_version: int,
                  instance_id: int = 0) -> bool:
        """乐观写入: 仅当版本号匹配时才写入。返回是否成功。"""
        if key in self._fields and self._fields[key].version != expected_version:
            return False
        self.write(key, value, instance_id)
        return True

    def batch_try_write(self, updates: dict[str, tuple[Any, int]],
                        instance_id: int = 0) -> dict[str, bool]:
        """批量乐观写入。每个字段独立检查版本。返回每个字段的写入结果。"""
        results = {}
        for key, (value, expected_version) in updates.items():
            results[key] = self.try_write(key, value, expected_version, instance_id)
        return results

    # ═══ 版本查询 ═══

    def get_version(self, key: str) -> int:
        return self._fields[key].version if key in self._fields else 0

    def get_meta(self, key: str) -> FieldMeta | None:
        return self._fields.get(key)

    def get_snapshot(self) -> dict:
        """获取完整状态快照（含版本信息）。"""
        return {
            "fields": {k: m.to_dict() for k, m in self._fields.items()},
            "created_at": self.created_at,
            "snapshot_at": time.time(),
        }

    # ═══ 异步安全 ═══

    async def async_write(self, key: str, value: Any, instance_id: int = 0):
        async with self._lock:
            self.write(key, value, instance_id)

    async def async_read(self, keys: list[str] | None = None) -> dict:
        async with self._lock:
            return self.read(keys)

    async def async_try_write(self, key: str, value: Any, expected_version: int,
                              instance_id: int = 0) -> bool:
        async with self._lock:
            return self.try_write(key, value, expected_version, instance_id)

    # ═══ 感知流集成 ═══

    def append_perception(self, perception: dict):
        """追加一条感知记录到感知流。"""
        if "perception_stream" not in self._fields:
            self._fields["perception_stream"] = FieldMeta(value=[], version=1)
        stream = self._fields["perception_stream"].value
        stream.append(perception)
        # 保持 60 秒窗口
        now = time.time()
        while stream and now - stream[0].get("t", 0) > 60:
            stream.pop(0)
        self._fields["perception_stream"].version += 1
        self._fields["perception_stream"].updated_at = now

    def get_perception_window(self, window_s: float = 10) -> list[dict]:
        """获取最近 N 秒的感知流切片。"""
        stream_meta = self._fields.get("perception_stream")
        if not stream_meta:
            return []
        stream = stream_meta.value
        cutoff = time.time() - window_s
        return [p for p in stream if p.get("t", 0) >= cutoff]

    # ═══ 工具 ═══

    def get_event_log(self, limit: int = 50) -> list[dict]:
        return list(self._event_log[-limit:])

    def __contains__(self, key: str) -> bool:
        return key in self._fields

    def keys(self) -> list[str]:
        return list(self._fields.keys())

    def __len__(self) -> int:
        return len(self._fields)

    def __repr__(self) -> str:
        ks = ", ".join(f"{k}(v{m.version})" for k, m in list(self._fields.items())[:5])
        return f"Blackboard({len(self._fields)} fields: {ks}...)"
