"""有限状态机 — 对话阶段管理。

FSM 提供确定性骨架，LLM 提供肌肉。
状态由 LLM 输出的 action 字段驱动转移，不依赖 LLM 推理状态。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class State(str, Enum):
    IDLE = "idle"           # 等待输入
    ANALYZE = "analyze"     # 理解意图
    PLAN = "plan"           # 制定计划
    EXEC = "exec"           # 执行工具
    VERIFY = "verify"       # 验证结果
    RESPOND = "respond"     # 生成回复


# 状态转移表: {当前状态: {事件: 下一状态}}
TRANSITIONS: dict[State, dict[str, State]] = {
    State.IDLE: {
        "user_input": State.ANALYZE,
        "initiative": State.RESPOND,  # 驱力驱动的主动行为
    },
    State.ANALYZE: {
        "understood": State.PLAN,        # 意图明确，需要工具
        "simple": State.RESPOND,         # 不需要工具，直接回复
        "unclear": State.RESPOND,        # 不理解，追问澄清
    },
    State.PLAN: {
        "need_tool": State.EXEC,
        "no_tool": State.RESPOND,
        "planned": State.EXEC,
    },
    State.EXEC: {
        "done": State.VERIFY,
        "error": State.PLAN,             # 工具执行失败，重新规划
        "timeout": State.RESPOND,        # 超时，告诉用户情况
    },
    State.VERIFY: {
        "success": State.RESPOND,
        "retry": State.EXEC,
        "fail": State.RESPOND,           # 验证失败，向用户解释
    },
    State.RESPOND: {
        "done": State.IDLE,              # 回复完成，等待下一轮
    },
}


@dataclass
class FSMContext:
    """FSM 上下文——状态转移时的附加数据。"""
    action: str = ""           # 触发转移的 action
    intent: str = ""           # 用户意图描述
    plan_steps: list[str] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    error: str = ""
    metadata: dict = field(default_factory=dict)


class FiniteStateMachine:
    """对话阶段有限状态机。

    用法:
        fsm = FiniteStateMachine()
        fsm.transition("user_input")
        print(fsm.state)  # State.ANALYZE
    """

    def __init__(self, initial_state: State = State.IDLE):
        self.state = initial_state
        self.previous_state = initial_state
        self.context = FSMContext()
        self._history: list[tuple[State, str, State]] = []  # (from, event, to)
        self._hooks: dict[State, list[Callable]] = {}  # 进入状态时的钩子

    def transition(self, event: str, context: FSMContext | None = None) -> State:
        """执行状态转移。返回新状态。"""
        if context:
            self.context = context

        valid_events = TRANSITIONS.get(self.state, {})
        if event not in valid_events:
            # 尝试部分匹配
            for key in valid_events:
                if key in event or event in key:
                    event = key
                    break
            else:
                # 无匹配事件，保持在当前状态
                return self.state

        next_state = valid_events[event]
        self.previous_state = self.state
        self._history.append((self.state, event, next_state))
        if len(self._history) > 50:
            self._history = self._history[-50:]

        # 执行进入钩子
        for hook in self._hooks.get(next_state, []):
            hook(self.context)

        self.state = next_state
        return next_state

    def on_enter(self, state: State):
        """装饰器: 注册进入状态的钩子。"""
        def decorator(func: Callable):
            self._hooks.setdefault(state, []).append(func)
            return func
        return decorator

    def can_transition(self, event: str) -> bool:
        """检查事件是否可触发状态转移。"""
        return event in TRANSITIONS.get(self.state, {})

    def available_events(self) -> list[str]:
        """当前状态下可用的转移事件列表。"""
        return list(TRANSITIONS.get(self.state, {}).keys())

    def history(self, n: int = 5) -> list[dict]:
        """最近 n 次状态转移的历史。"""
        return [
            {"from": f.value, "event": e, "to": t.value}
            for f, e, t in self._history[-n:]
        ]

    def reset(self):
        """重置到初始状态。"""
        self.state = State.IDLE
        self.previous_state = State.IDLE
        self.context = FSMContext()
