"""Multi-Agent System — 借鉴 OpenClaw sessions_send/spawn 模式

Agent 间通信:
- sessions_list: 查看活跃会话
- sessions_send: 给另一个会话发消息
- sessions_spawn: 创建新会话来委派任务
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AgentMessage:
    """Agent 间消息。"""
    from_agent: str
    to_agent: str
    content: str
    timestamp: float = field(default_factory=time.time)
    message_type: str = "text"  # text / task / result


@dataclass
class AgentRegistry:
    """多 Agent 注册表和消息总线。"""

    agents: dict[str, object] = field(default_factory=dict)  # {name: CharacterMind}
    messages: list[AgentMessage] = field(default_factory=list)
    max_messages: int = 200

    def register(self, name: str, mind: object):
        self.agents[name] = mind

    def unregister(self, name: str):
        self.agents.pop(name, None)

    def list_agents(self) -> list[str]:
        return list(self.agents.keys())

    def send(self, from_agent: str, to_agent: str, content: str,
             msg_type: str = "text") -> AgentMessage | None:
        if to_agent not in self.agents:
            return None
        msg = AgentMessage(from_agent=from_agent, to_agent=to_agent,
                          content=content, message_type=msg_type)
        self.messages.append(msg)
        self.messages = self.messages[-self.max_messages:]
        # 将消息注入目标 Agent 的感知流
        target = self.agents[to_agent]
        if hasattr(target, 'perceive'):
            target.perceive(content, source=from_agent, modality="dialogue",
                          intensity=0.6)
        return msg

    def spawn(self, from_agent: str, name: str, profile: dict,
              provider) -> object | None:
        """创建新 Agent 实例并委托任务。"""
        from character_mind.core.runtime_v2 import CharacterMind
        mind = CharacterMind(provider, profile)
        self.register(name, mind)
        # 通知创建者
        self.send(name, from_agent, f"[系统] Agent {name} 已创建并就绪", "task")
        return mind

    def get_messages_for(self, agent_name: str, n: int = 10) -> list[AgentMessage]:
        return [m for m in self.messages[-n * len(self.agents):]
                if m.to_agent == agent_name or m.from_agent == agent_name]

    def get_messages_between(self, agent_a: str, agent_b: str,
                            n: int = 10) -> list[AgentMessage]:
        return [m for m in self.messages
                if {m.from_agent, m.to_agent} == {agent_a, agent_b}][-n:]

    def to_dict(self) -> dict:
        return {
            "agents": self.list_agents(),
            "message_count": len(self.messages),
        }
