# Character Mind

**现象学 Agent 运行时。**

基于 CLARION 认知架构、Scherer 评估理论、现象学时间意识模型和 Hermes/OpenClaw Agent 模式，Character Mind 将 24 个心理学模型、五层认知管线、连续意识循环、记忆新陈代谢、技能生命周期和现实世界反馈闭环整合为一个可部署的角色智能体。

```python
from character_mind import CharacterMind

mind = CharacterMind(provider, {
    "name": "林雨",
    "personality": {"openness": 0.6, "neuroticism": 0.75, "attachment_style": "anxious"},
    "trauma": {"active_schemas": ["遗弃/不稳定"]},
})

mind.perceive("陈风两小时没回消息", source="陈风")
await mind.runtime.tick_once()
response = mind.get_response()
print(response.text)  # "没回，刚在忙。" (回避型防御 + 恐惧潜台词)
```

---

## 架构

```
┌─────────────────────────────────────────────┐
│         PhenomenologicalRuntime             │
│         (持续 tick 循环, 200-500ms)          │
│                                             │
│  Perception → ThalamicGate → Consciousness  │
│       ↓              ↓            ↓         │
│  [预测误差]  →  [GWT 工作空间]  →  [体验场]  │
│       ↓                                    │
│  Cognitive Frame (orchestrator L0-L5)       │
│       ↓                                    │
│  SelfModel → InnerStream → ExpressionPolicy  │
│       ↓                                    │
│  BehaviorStream → 外部世界                   │
│                                             │
│  后台: MemoryMetabolism, SkillLifecycle,     │
│        NoiseManager, FeedbackLoop, LoveState │
└─────────────────────────────────────────────┘
```

### 认知管线 (Cognitive Frame — 情感脑 + 社会脑)

| 层 | 功能 | Skill |
|----|------|-------|
| L-3 生物 | 驱力 · HPA · 递质 · LoveState | BiologicalBridge |
| L0 人格 | 我是谁？ | BigFive · Attachment |
| L1 情绪 | 我感受什么？ | Plutchik · PTSDTrigger |
| L2 评价 | 这对我意味着什么？ | OCC · DefenseMechanism |
| L3 社交 | 别人在想什么？ | TheoryOfMind · Gottman · Foucault |
| L4 反思 | 如何调节？ | GrossRegulation · SDT |
| L5 回应 | 说什么/做什么？ | ResponseGenerator |

**关键设计**: L0-L3 频繁脉冲 (~1-3s 或预测误差大时), L4-L5 条件触发。中间 tick 由零 token 数学模型桥接。

### 意识流系统

| 组件 | 功能 | 脑对应 |
|------|------|--------|
| ThalamicGate | 预测误差驱动感知过滤 | 丘脑 Pulvinar + VIP |
| ConsciousnessLayer | GWT 工作空间(容量4) + EWMA 预测 | PFC-后部同步 |
| ExperientialField | Retention(滞留) + Protention(前摄) | Precuneus |
| InnerExperienceStream | 私密内部体验流 | DMN 自发思维 |
| SelfModel | vmPFC(情境)/amPFC(他人)/dmPFC(行动) | DMN 三模块 |
| ExpressionPolicy | masking/omission 内部→外部 | 基底节策略选择 |

### 记忆系统 (Hermes 三层 + 五级代谢)

```
Layer 1: SOUL.md + MEMORY.md (黄金指针, 始终在上下文)
Layer 2: fact_store + skills (tag/FTS5 检索)
Layer 3: 语义向量 + 时间线索引 (高投资分析)

代谢流: Working → Short → Long → Core(永久) ∥ Archive(淘汰)
```

### 智能体基础设施

| 系统 | 功能 |
|------|------|
| Workspace | SOUL/AGENTS/MEMORY/TOOLS + config.json |
| Session | main/dm/group/cron, TrustLevel, 沙箱 |
| Tools | bash/file/session/memory, 条件可用性 |
| Multi-Agent | sessions_send/spawn, AgentRegistry |
| Cron | 定时任务, JSON 持久化, 独立 CharacterMind |
| Skill Lifecycle | active→idle→archive, Curator 审查 |
| ContextAssembly | 系统提示缓存, 标签隔离, 15 种注入扫描 |
| FeedbackLoop | WorldAdapter → 模式提取 → 知识固化 |
| NoiseManager | 噪音率查询 + 自动清理 |
| LoveState | Fisher 三阶段, 递质调制, PFC 抑制 |

---

## 为什么不是角色卡

```
角色卡:
  "她是一个焦虑型依恋的人，害怕被抛弃。"
  → LLM 自行揣摩

Character Mind:
  L-3 生物 → CORT=0.6, 情绪衰减延长, 负面情绪更持久
  L0 人格  → 高神经质(N=0.75), 模糊信号做负面解读
  L1 情绪  → 主导 fear=0.7, 内部恐惧 vs 外部平静 (情绪差距)
  L2 防御  → 投射激活: 被抛弃恐惧→归因为对方冷漠
  L3 社交  → TheoryOfMind: 对方可能想离开我
  L5 回应  → "没回，刚在忙。" (回避型防御 + 不翻译潜台词)
  ═══════════════════════════════════════
  体验场   → "刚刚过去的还在回响: 等待的焦虑"
  记忆代谢 → 类似事件: 上次他也这样, 后来离开了
  内部体验 → "希望他立刻证明还在乎我" [不可直接表达]
  表达策略 → masking: 内部渴望→外部冷淡
```

---

## 快速开始

```bash
pip install openai
```

### v2 API (推荐)

```python
from character_mind import CharacterMind
from character_mind.benchmark.real_llm_benchmark import DeepSeekProvider

provider = DeepSeekProvider(
    api_key="sk-xxx", model="deepseek-chat", thinking=False,
)

mind = CharacterMind(provider, {
    "name": "林雨",
    "personality": {
        "openness": 0.6, "neuroticism": 0.75,
        "attachment_style": "anxious",
        "defense_style": ["投射", "合理化"],
    },
    "trauma": {
        "ace_score": 2,
        "active_schemas": ["遗弃/不稳定"],
        "trauma_triggers": ["被忽视", "被抛弃"],
    },
})

mind.perceive("陈风两小时没回消息", source="陈风")
await mind.runtime.tick_once()
resp = mind.get_response()
print(resp.text)       # "没回，刚在忙。"
print(resp.emotion)    # "fear"
print(resp.subtext)    # "为什么不回我...是不是不在乎了"
```

### v1 API (向后兼容)

```python
from character_mind import create_runtime

runtime = create_runtime(anti_alignment_enabled=True)
result = await runtime.orchestrator.process_event(provider, character_state, event)
print(result.combined_analysis)
```

### CLI

```bash
python cli.py chat                      # 终端交互 (MockProvider)
python cli.py chat --provider ollama    # 终端交互 (lfm2.5 本地)
python cli.py serve                     # 启动 Gateway (:18790)
python cli.py status                    # 运行时状态
```

---

## 质量验证

DeepSeek Flash (no thinking), 6 场景, LLM-as-Judge 7 维度:

| 维度 | 分数 |
|------|------|
| 情感真实性 | 5.0 |
| 人格一致性 | 5.0 |
| 留白与潜台词 | 5.0 |
| 防御机制 | 4.7 |
| 关系敏感性 | 4.7 |
| 情感深度 | 4.2 |
| 心理矛盾性 | 4.2 |
| **综合质量** | **0.91** |

---

## 测试

```bash
# 全量 (145 tests)
python -m unittest discover -s tests/experimental -p "test_*.py" -v

# LLM-as-Judge 质量基准
python benchmark/real_llm_benchmark.py --provider deepseek --think 0 --bio 1 --scenarios 6
```

---

## 项目结构

```
core/                     # 认知引擎 + Agent 基础设施
  runtime_v2.py           # CharacterMind v2 生产 API
  orchestrator.py         # Cognitive Frame (五层编排器)
  context_assembly.py     # 系统提示缓存 + 注入扫描
  workspace.py            # SOUL/AGENTS/MEMORY/TOOLS
  session.py              # 会话管理 + TrustLevel
  tools.py                # ToolRegistry + 条件可用性
  multi_agent.py          # AgentRegistry + 消息总线
  cron.py                 # 定时任务调度器
  base.py, registry.py    # Skill 基类 + 注册表
  emotion_decay.py        # PAD 双速衰减
  episodic_memory.py      # 情景记忆
  personality_state_machine.py  # 人格状态机
  emotion_vocabulary.py   # 80+ 情感词汇
  biological/             # 生物基础层 (可选)

experimental/             # 现象学 Agent 运行时
  phenomenological_runtime.py  # 主 tick 循环
  consciousness.py        # GWT + 预测加工 (零 token)
  thalamic_gate.py        # 感知门控
  memory_metabolism.py    # 五级记忆代谢
  experiential_field.py   # Retention + Protention
  inner_experience.py     # 私密内部体验流
  expression_policy.py    # 内部→外部转换
  world_adapter.py        # 外部反馈入口
  skill_metabolism.py     # 技能生命周期
  noise_manager.py        # 噪音管理
  love_state.py           # Fisher 爱情调制
  feedback_loop.py        # 反馈闭环

gateway/                  # HTTP + WebSocket + 通道
skills/                   # 24 个心理学 Skill
benchmark/                # LLM-as-Judge 基准
tests/                    # 145 tests
cli.py                    # CLI 入口
```

---

## 成本

单次 Cognitive Frame: ~7,000 tokens。系统提示固定 → 缓存命中率接近 100%。

| 场景 | 调用/h | Flash 缓存命中 |
|------|--------|---------------|
| 聊天 (30 msg/h) | 60 | RMB 0.13/h |
| 直播 (4/min) | 240 | RMB 0.53/h |
| LLM 脉冲 (2s) | 1,800 | RMB 3.99/h |

---

## License

MIT
