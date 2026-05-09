# Character Mind

**现象学 Agent 运行时。** 基于 CLARION 认知架构、Scherer 评估理论和连续意识模型的角色心理引擎。

24 个心理学模型通过五层认知管线（L0 人格 → L1 情绪 → L2 评价 → L3 社交 → L4 反思 → L5 回应）对事件做分层并行/串行处理。不是给 LLM 一段文字描述角色，而是告诉 LLM 这个角色在此刻会怎么想、怎么感受、怎么回应。

```python
from character_mind import CharacterMind

mind = CharacterMind(provider, {
    "name": "林雨",
    "personality": {"openness": 0.6, "neuroticism": 0.75, "attachment_style": "anxious"},
    "trauma": {"active_schemas": ["遗弃/不稳定"]},
})

mind.perceive("陈风两小时没回消息", source="陈风")
await mind.runtime.tick_once()
resp = mind.get_response()
print(resp.text)    # "没回，刚在忙。"
print(resp.emotion) # "fear"
```

---

## 架构

```
Perception → ThalamicGate → ConsciousnessLayer (预测+workspace)
                                  ↓
                           Cognitive Frame (L0-L5 orchestrator)
                                  ↓
                      SelfModel → InnerStream → ExpressionPolicy
                                  ↓
                           BehaviorStream → 外部
```

### 认知管线 (Cognitive Frame)

| 层 | 功能 | Skill |
|----|------|-------|
| L-3 | 驱力 · HPA · 递质 | BiologicalBridge (可选) |
| L0 | 我是谁？ | BigFive · Attachment |
| L1 | 我感受什么？ | Plutchik · PTSDTrigger |
| L2 | 这对我意味着什么？ | OCC · DefenseMechanism |
| L3 | 别人在想什么？ | TheoryOfMind · Gottman · Foucault |
| L4 | 如何调节？ | GrossRegulation · SDT |
| L5 | 说什么/做什么？ | ResponseGenerator |

**运行模式**: L0-L3 预测误差驱动触发 (~1-3s), L4-L5 条件触发。tick 间由零 token 数学模型桥接（情感衰减、驱动演化、预测加工）。

### 意识流系统

| 组件 | 功能 | 脑对应 |
|------|------|--------|
| ThalamicGate | 预测误差驱动感知过滤, 82 种情绪关键词 | 丘脑 Pulvinar |
| ConsciousnessLayer | GWT 工作空间(4), EWMA+自适应alpha 预测 | PFC-后部同步 |
| ExperientialField | Retention(滞留衰减) + Protention(前摄散布) | Precuneus |
| InnerExperienceStream | 私密内部流 (felt_emotion/conflict/intention/forbidden_wish) | DMN |
| ExpressionPolicy | masking/omission/direct — 内部→外部转换 | 基底节 |

### 记忆系统

```
Layer 1: soul.md + memory_index.md (黄金指针, 始终注入)
Layer 2: fact_store + skills (tag/FTS5 检索)
Layer 3: 语义向量 + 时间线检索

代谢流: Working → Short → Long → Core(永久) ∥ Archive(淘汰)
```

### 智能体基础设施

| 系统 | 功能 |
|------|------|
| Workspace | SOUL/AGENTS/MEMORY/TOOLS + config.json |
| Session | main/dm/group/cron, TrustLevel, 沙箱 |
| Tools | bash/file/session/memory, 条件可用性 |
| Multi-Agent | AgentRegistry, sessions_send/spawn |
| Cron | 定时任务, JSON 持久化 |
| Skill Lifecycle | active→idle→archive, Curator |
| ContextAssembly | 系统提示缓存, 15 种注入扫描 |
| FeedbackLoop | WorldAdapter → 模式提取 → 知识固化 |
| NoiseManager | 噪音率查询 + 自动清理 |
| LoveState | Fisher 三阶段 (Lust→Attraction→Attachment) |

---

## 为什么不是角色卡

```
角色卡:
  "她是一个焦虑型依恋的人，害怕被抛弃。"
  → LLM 自行揣摩

Character Mind:
  L0 人格  → 高神经质(N=0.75), 模糊信号做负面解读
  L1 情绪  → 主导 fear=0.7, 内部恐惧 vs 外部平静
  L2 防御  → 投射: 被抛弃恐惧→归因为对方冷漠
  L3 社交  → TheoryOfMind: 对方可能想离开我
  L5 回应  → "没回，刚在忙。" (不翻译潜台词)
  ════════════════════════════════
  内部体验 → "希望他立刻证明还在乎我" [不可表达]
  表达策略 → masking: 内部渴望→外部冷淡
  记忆代谢 → 类似事件: 上次他也这样
```

---

## 快速开始

```bash
pip install openai
```

### v2 API

```python
from character_mind import CharacterMind

mind = CharacterMind(provider, character_profile)
mind.perceive("事件描述", source="对方")
await mind.runtime.tick_once()
resp = mind.get_response()
```

### v1 API (向后兼容)

```python
from character_mind import create_runtime

runtime = create_runtime()
result = await runtime.orchestrator.process_event(provider, character_state, event)
```

### CLI

```bash
python cli.py chat                      # 终端交互 (MockProvider)
python cli.py chat --provider ollama    # 终端交互 (本地模型)
python cli.py serve                     # 启动 Gateway (:18790)
```

### 测试

```bash
python -m unittest discover -s tests/experimental -p "test_*.py" -v
python benchmark/real_llm_benchmark.py --provider deepseek --think 0 --bio 1 --scenarios 6
```

---

## 质量

DeepSeek Flash, 6 场景, LLM-as-Judge 7 维度:

| 维度 | 分数 |
|------|------|
| 情感真实性 | 5.0 |
| 人格一致性 | 5.0 |
| 留白与潜台词 | 5.0 |
| 防御机制 | 4.7 |
| 关系敏感性 | 4.7 |
| 综合质量 | **0.91** |

123 tests, 20.9s, 全过。

---

## 项目结构

```
core/                     # 认知引擎 + Agent 基础设施
  runtime_v2.py           # CharacterMind v2 API
  orchestrator.py         # Cognitive Frame (L0-L5)
  base.py                 # Skill 基类, JSON 修复
  registry.py             # Skill 注册表
  workspace.py            # SOUL/AGENTS/MEMORY/TOOLS
  context_assembly.py     # 提示缓存 + 注入扫描
  session.py              # 会话 + TrustLevel
  tools.py                # 工具系统 + 条件可用性
  multi_agent.py          # Agent 注册表 + 消息总线
  cron.py                 # 定时任务调度
  skill_curator.py        # 技能审查器
  emotion_decay.py        # PAD 双速衰减
  episodic_memory.py      # 情景记忆
  personality_state_machine.py  # 人格状态机
  emotion_vocabulary.py   # 80+ 情感词汇
  biological/             # 生物基础层 (可选)

experimental/             # 现象学运行时 (14 模块)
  phenomenological_runtime.py  # 主 tick 循环
  consciousness.py        # GWT + EWMA 预测
  thalamic_gate.py        # 感知门控
  memory_metabolism.py    # 五级记忆代谢
  experiential_field.py   # Retention + Protention
  inner_experience.py     # 私密内部流
  expression_policy.py    # 内部→外部转换
  world_adapter.py        # 外部反馈
  skill_metabolism.py     # 技能生命周期
  noise_manager.py        # 噪音管理
  love_state.py           # Fisher 爱情调制
  feedback_loop.py        # 反馈闭环
  blackboard.py           # 版本化共享状态
  perception_stream.py    # 感知流
  behavior_stream.py      # 行为流

skills/                   # 24 心理学 Skill (L0-L5)
gateway/                  # HTTP + WebSocket + 通道
benchmark/                # LLM-as-Judge + MockProvider
tests/                    # 123 tests
cli.py                    # CLI 入口
```

---

## 成本 (DeepSeek Flash)

| 场景 | RMB/h |
|------|-------|
| 聊天 30msg/h | 0.13 |
| 直播 4次/min | 0.53 |

---

## License

MIT
