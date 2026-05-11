"""RL 微调接口 (Stub) — 为将来的 RL 微调预留。

抄 MetaClaw + WebRL 的设计:
- 轨迹收集: 记录每轮 (state, action, reward, next_state)
- 进程奖励模型 (PRM): 评估轨迹质量
- LoRA 微调触发: 空闲窗口 + 轨迹积累 > 阈值
- 版本隔离: 微调用旧数据，新数据不断代

当前状态: 只做轨迹收集和 JSONL 导出，不做训练。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field


@dataclass
class TrajectoryStep:
    """单步轨迹"""
    state: str              # 用户输入 + 上下文摘要
    action: str             # 助手回应
    reward: float = 0.0     # 奖励信号 (-1 到 1)
    next_state: str = ""    # 下一步状态


@dataclass
class Trajectory:
    """完整交互轨迹"""
    trajectory_id: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    total_reward: float = 0.0
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)


class RLInterface:
    """RL 微调接口 — 轨迹收集 + 导出。暂不做训练。"""

    def __init__(self, min_trajectories: int = 100):
        self.min_trajectories = min_trajectories
        self._trajectories: list[Trajectory] = []
        self._current_trajectory: Trajectory | None = None
        self._counter: int = 0

    def start_trajectory(self, context: str = ""):
        """开始一个新的交互轨迹。"""
        self._counter += 1
        self._current_trajectory = Trajectory(
            trajectory_id=f"traj_{self._counter}_{int(time.time())}",
            timestamp=time.time(),
            metadata={"context": context[:200]},
        )

    def add_step(self, user_input: str, assistant_response: str,
                 reward: float = 0.0):
        """添加一步轨迹。"""
        if not self._current_trajectory:
            self.start_trajectory()

        step = TrajectoryStep(
            state=user_input[:500],
            action=assistant_response[:500],
            reward=max(-1.0, min(1.0, reward)),
        )

        # 使用心理学引擎的 quality 评分作为 reward
        if reward == 0.0:
            # 默认: 基于回应长度和基本质量给分
            if len(assistant_response) > 10 and len(assistant_response) < 500:
                step.reward = 0.1  # 及格分
            elif len(assistant_response) >= 500:
                step.reward = -0.1  # 太长

        self._current_trajectory.steps.append(step)

    def end_trajectory(self, overall_reward: float = 0.0):
        """结束当前轨迹。"""
        if self._current_trajectory and self._current_trajectory.steps:
            # 累计奖励
            for step in self._current_trajectory.steps:
                self._current_trajectory.total_reward += step.reward
            # 整体奖励加成
            self._current_trajectory.total_reward += overall_reward
            self._trajectories.append(self._current_trajectory)
        self._current_trajectory = None

        # 限制总数
        if len(self._trajectories) > 1000:
            self._trajectories = self._trajectories[-1000:]

    def should_trigger_ft(self) -> bool:
        """是否达到微调阈值。"""
        return len(self._trajectories) >= self.min_trajectories

    def export_jsonl(self, format: str = "openai") -> str:
        """导出为微调格式 JSONL。

        OpenAI 格式: {"messages": [{"role":"system",...}, {"role":"user",...}, {"role":"assistant",...}]}
        """
        lines = []
        for traj in self._trajectories:
            for step in traj.steps:
                if step.reward > 0:  # 只导出正奖励的样本
                    record = {
                        "messages": [
                            {"role": "system", "content": traj.metadata.get("context", "")},
                            {"role": "user", "content": step.state},
                            {"role": "assistant", "content": step.action},
                        ],
                        "metadata": {
                            "reward": step.reward,
                            "trajectory_id": traj.trajectory_id,
                            "total_reward": traj.total_reward,
                        },
                    }
                    lines.append(json.dumps(record, ensure_ascii=False))
        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "total_trajectories": len(self._trajectories),
            "total_steps": sum(len(t.steps) for t in self._trajectories),
            "avg_reward": (
                sum(t.total_reward for t in self._trajectories) / max(len(self._trajectories), 1)
            ),
            "ready_for_ft": self.should_trigger_ft(),
            "positive_samples": sum(
                1 for t in self._trajectories for s in t.steps if s.reward > 0
            ),
        }
