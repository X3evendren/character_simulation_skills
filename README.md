# Character Mind

为 LLM 角色扮演提供结构化心理引擎。不是 prompt template，不是角色卡——是一套运行在 LLM 之上的**认知架构**，让角色拥有可追溯的心理因果链。

```
"他为什么那样回复？" → L0 人格偏置 → L1 情绪激活 → L2 防御机制 → L3 权力/关系 → L5 回应
```

---

## 它是什么 / 不是什么

**是:**
- 一个可嵌入的认知处理管线，输入事件 + 角色档案，输出有心理深度的角色回应
- 基于 11 个互补心理学框架的分层引擎，每层回答不同的问题
- 自带神经递质引擎、HPA 轴、内稳态驱力系统的生物基础层
- LLM 无关——DeepSeek、OpenAI、Ollama 均可接入

**不是:**
- 角色扮演 chatbot（没有对话界面，不处理多轮对话逻辑）
- prompt engineering 模板集合（每个 Skill 是独立的 LLM 调用）
- 人格测试工具（不评估真实人类，只驱动虚构角色）

---

## 架构

### 认知管线

```
事件 → [生物层更新] → L0 → L1 → L2 → L3 → L4 → L5 → 回应/行为
         ↑ 驱力·递质·HPA                              ↓ 状态写回
         └────────────── 同层并行 · 跨层串行 ←──────────┘
```

| 层 | 回答的问题 | 活跃 Skill | 触发 |
|----|-----------|-----------|------|
| **L-3 驱力** | 我想要什么？ | 15 驱力系统 + W-Learning 行动选择 | 持续 |
| **L-2 递质** | 我的生物状态？ | DA/5-HT/NE/CORT/OXT + 受体适应 | 持续 |
| **L-2 HPA** | 我有多紧张？ | CRH→ACTH→CORT→GR ODE | 持续 |
| **L-1 推理** | 我预期什么？ | 精度加权 + 预期自由能 + 信念更新 | 持续 |
| **L0 人格** | 我是什么样的人？ | BigFive, Attachment | always / social |
| **L1 情绪** | 我感受到什么？ | Plutchik, PTSDTrigger | always / trauma |
| **L2 评价** | 这对我意味着什么？ | OCC, DefenseMechanism | always |
| **L3 社交** | 别人在想什么？ | TheoryOfMind, Gottman, Foucault | 条件触发 |
| **L4 反思** | 我该如何调节？ | GrossRegulation, SDT | sig ≥ 0.7 |
| **L5 回应** | 我该说什么/做什么？ | ResponseGenerator + 条件创伤 | always |

### Agent 循环

```
while event:
    bio.update(dt, event)          # 驱力衰减 · 递质更新 · HPA应激
    ctx = bio.get_context()        # 精度权重 · 行动倾向 · 调制参数
    ctx = decay.emotions()         # CORT 调节半衰期
    ctx = memory.retrieve(event)   # 情景记忆检索

    for layer in [L0, L1, L2, L3, L4, L5]:
        results[layer] = await parallel_run(layer.skills, ctx)

    response = results[L5].response_text
    bio.feedback(response)         # 驱力满足 · 递质反馈
    memory.store(event, results)   # 持久化
```

---

## 快速开始

```bash
pip install openai
```

```python
import asyncio
from character_mind import get_orchestrator
from character_mind.core.biological import BiologicalBridge

# 生物基础层 — OCEAN 自动映射到递质基线
bio = BiologicalBridge()
bio.set_character_profile(
    ocean={"extraversion": 0.4, "neuroticism": 0.75, "openness": 0.6,
           "conscientiousness": 0.5, "agreeableness": 0.55},
    attachment="anxious", ace=2,
)

async def main():
    result = await get_orchestrator(
        anti_alignment_enabled=True, biological_bridge=bio
    ).process_event(
        provider,  # DeepSeek / OpenAI / Ollama
        character_state={"personality": {...}, "trauma": {...}},
        event={"description": "陈风两小时没回消息", "type": "social",
               "significance": 0.5, "participants": [{"name": "陈风", "relation": "partner"}]},
    )
    print(result.combined_analysis)  # 角色的回应文本
    print(result.total_tokens)       # 本次处理消耗的 token
```

---

## 特性

**核心心理引擎**
- 五层认知管线，层内并行 · 层间串行
- PAD 三维情感空间 + 双速衰减（CORT 调制半衰期）
- 情景记忆（时序边 + 情感标签 + 优先级淘汰）
- 人格状态机（OCEAN 基线 + 8 情境状态 + 逐轮微调）
- 反 RLHF 偏差注入（Silence Rule，开放性条件自适应）

**生物基础层**（独立于认知管线，可选启用）
- 15 驱力内稳态（Tyrrell 分层 + Panksepp SEEKING/PLAY/PANIC）
- 完整 HPA 轴 ODE（CRH→ACTH→CORT→GR，ACE 参数化）
- 5 递质引擎（DA/5-HT/NE/CORT/OXT），OCEAN→基线，受体适应，跨递质交互
- 主动推理桥接（精度加权，预期自由能，信念更新）

**质量评估**
- LLM-as-Judge 七维度评分（DeepSeek V4 Pro）
- 情感真实性 / 人格一致性 / 防御表达 / 情感深度 / 关系敏感性 / 潜台词克制 / 心理矛盾性
- 5,960 条多源测试用例（CPED、CharacterBench、EmpatheticDialogues 等 9 个数据集）

**工程特性**
- 26 个心理学 Skill，插件式注册，独立 LLM 调用
- Provider 无关——DeepSeek / OpenAI / Ollama 统一接口
- 全管线 JSON 可序列化，状态可持久化
- MockProvider 快速回归测试

---

## 质量

LLM-as-Judge 七维度评分（DeepSeek V4 Pro thinking），最优配置 0.98，详见 [benchmark](benchmark/)。

---

## 项目结构

```
core/                          # 核心引擎
  orchestrator.py              # 五层编排器
  base.py                      # Skill 基类 + JSON 提取
  registry.py                  # Skill 注册表
  emotion_decay.py             # PAD 情感衰减 (CORT 调制)
  episodic_memory.py           # 情景记忆
  personality_state_machine.py # 人格状态机
  emotion_vocabulary.py        # 80+ 情感词汇
  biological/                  # 生物基础层
    drive_system.py            # L-3: 15 驱力 + W-Learning
    hpa_axis.py                # L-2b: HPA 轴 ODE
    neurotransmitter.py        # L-2a: 5 递质引擎
    active_inference.py        # L-1: 主动推理桥接
    biological_bridge.py       # 集成适配器
skills/                        # 26 个心理学 Skill (5 层)
benchmark/
  real_llm_benchmark.py        # LLM-as-Judge 基准
  mock_provider.py             # Mock LLM 测试
tests/validation/              # 5,960 用例回归测试
docs/superpowers/specs/        # 设计文档
```

---

## 测试

```bash
# LLM-as-Judge (需要 DeepSeek API Key)
python benchmark/real_llm_benchmark.py --provider deepseek --think 1 --bio 1

# Mock 快速基准
python benchmark/improved_benchmark.py

# 回归验证 (5,960 用例)
python tests/validation/run_validation.py
```

---

MIT · [设计文档](docs/superpowers/specs/) · 基于 CLARION 认知架构 + Scherer 评估理论
