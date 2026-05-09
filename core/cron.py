"""Cron Scheduler — 借鉴 Hermes cron/scheduler + OpenClaw Cron

定时任务: 用 CharacterMind 实例在指定时间自主运行。
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field


@dataclass
class CronJob:
    """单个定时任务。"""
    name: str
    schedule: str           # cron 表达式 (简化为间隔秒数或 "daily_9am")
    prompt: str             # 触发时执行的任务描述
    character_profile: dict # 角色配置
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0
    run_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "schedule": self.schedule,
            "prompt": self.prompt,
            "character_profile": self.character_profile,
            "enabled": self.enabled, "last_run": self.last_run,
            "next_run": self.next_run, "run_count": self.run_count,
        }


class CronScheduler:
    """轻量级 Cron 调度器 (asyncio)。

    调度格式:
    - "*/N" 或 "N": 每 N 秒
    - "daily_9am": 每天 9 点
    - "hourly": 每小时
    """

    def __init__(self, jobs_dir: str | None = None):
        self.jobs: dict[str, CronJob] = {}
        self.jobs_dir = jobs_dir or os.path.expanduser("~/.character_mind/cron")
        self.running = False
        self._task: asyncio.Task | None = None
        self.provider = None

    def add_job(self, name: str, schedule: str, prompt: str,
                character_profile: dict):
        job = CronJob(name=name, schedule=schedule, prompt=prompt,
                     character_profile=character_profile)
        job.next_run = time.time() + self._parse_interval(schedule)
        self.jobs[name] = job

    def remove_job(self, name: str):
        self.jobs.pop(name, None)

    def _parse_interval(self, schedule: str) -> float:
        """解析调度字符串为秒数。"""
        s = schedule.strip()
        if s.startswith("*/"):
            return float(s[2:])
        if s.replace(".", "").isdigit():
            return float(s)
        if s == "hourly":
            return 3600.0
        if s == "daily_9am":
            now = time.localtime()
            target = time.mktime((now.tm_year, now.tm_mon, now.tm_mday,
                                  9, 0, 0, 0, 0, 0))
            if target < time.time():
                target += 86400
            return target - time.time()
        return 3600.0  # 默认每小时

    async def start(self):
        self.running = True
        os.makedirs(self.jobs_dir, exist_ok=True)
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _loop(self):
        while self.running:
            now = time.time()
            for job in list(self.jobs.values()):
                if not job.enabled:
                    continue
                if now >= job.next_run:
                    await self._run_job(job)
                    job.last_run = now
                    job.run_count += 1
                    job.next_run = now + self._parse_interval(job.schedule)
            await asyncio.sleep(1)

    async def _run_job(self, job: CronJob):
        """执行一次 Cron 任务: 创建临时 CharacterMind, 运行一个 tick。"""
        if self.provider is None:
            return
        from character_mind.core.runtime_v2 import CharacterMind
        mind = CharacterMind(self.provider, job.character_profile, tick_interval=0.1)
        mind.perceive(job.prompt, source="cron", modality="internal", intensity=0.7)
        await mind.runtime.tick_once()
        resp = mind.get_response()

        # 保存输出
        output_dir = os.path.join(self.jobs_dir, job.name)
        os.makedirs(output_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"{ts}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "job": job.name, "timestamp": time.time(),
                "prompt": job.prompt,
                "response": resp.text, "emotion": resp.emotion,
                "stats": mind.stats(),
            }, f, ensure_ascii=False, indent=2)

    def save_jobs(self):
        os.makedirs(self.jobs_dir, exist_ok=True)
        path = os.path.join(self.jobs_dir, "jobs.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self.jobs.items()},
                     f, ensure_ascii=False, indent=2)

    def load_jobs(self):
        path = os.path.join(self.jobs_dir, "jobs.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                for name, d in data.items():
                    job = CronJob(name=name, schedule=d["schedule"],
                                 prompt=d.get("prompt", ""),
                                 character_profile=d.get("character_profile", {}))
                    job.enabled = d.get("enabled", True)
                    job.last_run = d.get("last_run", 0)
                    job.run_count = d.get("run_count", 0)
                    job.next_run = time.time() + self._parse_interval(job.schedule)
                    self.jobs[name] = job
