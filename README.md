# Character Mind

**LLM 角色扮演的心理引擎。** 一套运行在 LLM 之上的分层认知架构。输入事件 + 角色档案，输出有心理因果链的角色行为。

```python
from character_mind import create_runtime

runtime = create_runtime(anti_alignment_enabled=True)

result = await runtime.orchestrator.process_event(
    provider,
    character_state={"personality": {...}, "trauma": {...}},
    event={"description": "陈风两小时没回消息", "type": "social", "significance": 0.6},
)
print(result.combined_analysis)
```

`create_runtime()` 返回独立会话实例——内置 24 个心理学 Skill 自动注册，记忆和情绪状态按会话隔离。

---

## 架构

```
事件 → [生物层] → L0 人格 → L1 情绪 → L2 评价 → L3 社交 → L4 反思 → L5 回应
        ↑ 驱力·递质·HPA                           ↓ 状态写回
        └──── 同层并行 · 跨层串行 ──────────────────┘
```

| 层 | 做什么 | 活跃 Skill |
|----|--------|-----------|
| **L-3 生物** | 我想要什么？ | 15 驱力 + HPA 轴 + 5 递质 + 主动推理 |
| **L0 人格** | 我是什么样的人？ | BigFive · Attachment |
| **L1 情绪** | 我感受到什么？ | Plutchik · PTSDTrigger |
| **L2 评价** | 这对我意味着什么？ | OCC · DefenseMechanism |
| **L3 社交** | 别人在想什么？ | TheoryOfMind · Gottman · Foucault |
| **L4 反思** | 该如何调节？ | GrossRegulation · SDT |
| **L5 回应** | 该说什么/做什么？ | ResponseGenerator + 条件创伤 |

生物基础层将 OCEAN 人格自动映射为 DA/5-HT/NE/CORT/OXT 递质基线，CORT 调节情绪衰减半衰期，驱力状态影响行为优先级。

---

## 为什么不是角色卡

角色卡给 LLM 一段文字描述。Character Mind 给 LLM **11 个互补心理学框架的并行分析结果**。

```
角色卡:  "她是一个焦虑型依恋的人，害怕被抛弃。"

Character Mind:
  L0 人格 → 高神经质，行为偏置: 对模糊信号做负面解读
  L1 情绪 → 主导情绪 fear=0.7，内部恐惧 vs 外部表达为信任 (情绪差距)
  L2 防御 → 投射: 将自己的被抛弃恐惧归因为对方的冷漠
  L3 社交 → Gottman: 检测到批评和防御性回应模式
  L5 回应 → "你怎么这么久才回？不是说好了吗。"
             ↑ 含防御机制的行为输出，非解释性独白
```

---

## 特性

| 类别 | 内容 |
|------|------|
| **认知管线** | 5 层编排，11 个活跃 Skill，同层并行 · 跨层串行 |
| **生物基础** | 驱力内稳态 · HPA 轴 ODE · 递质引擎 · 主动推理桥接 |
| **情感系统** | PAD 三维空间 · CORT 调制半衰期 · 80+ 细粒度情感词 · 16 功能情感 |
| **记忆** | 情景记忆（时序边 + 情感标签 + 优先级淘汰）· 人格状态机 |
| **质量评估** | LLM-as-Judge 七维度（情感真实 · 人格一致 · 防御表达 · 情感深度 · 关系敏感 · 潜台词 · 心理矛盾） |
| **测试** | 5,960 用例 · 9 数据集适配器 · 运行时契约测试 |
| **LLM** | DeepSeek · OpenAI · Ollama · 统一 Provider 接口 |

---

## 项目结构

```
core/                     # 认知引擎
  orchestrator.py         # 五层编排器
  base.py                 # Skill 基类 · JSON 提取
  registry.py             # Skill 注册表 (profile-driven)
  runtime.py              # SessionRuntime 工厂
  runtime_profile.py      # 默认运行图声明
  emotion_decay.py        # PAD 双速衰减 (CORT 调制)
  episodic_memory.py      # 情景记忆
  personality_state_machine.py  # 人格状态机
  emotion_vocabulary.py   # 80+ 情感词汇
  biological/             # 生物基础层 (可选启用)
skills/                   # 24 个心理学 Skill (5 层)
benchmark/                # LLM-as-Judge 基准
tests/                    # 运行时测试 · 回归验证
experimental/             # 实验子系统 (TOCA/Blackboard/Consolidation)
```

---

## 快速开始

```bash
pip install openai
```

```python
import asyncio
from character_mind import create_runtime
from character_mind.core.biological import BiologicalBridge

# Provider — 任何兼容 OpenAI 接口的 LLM
class MyProvider:
    async def chat(self, messages, temperature, max_tokens):
        ...

# 可选的生物基础层
bio = BiologicalBridge()
bio.set_character_profile(
    ocean={"extraversion": 0.4, "neuroticism": 0.75, "openness": 0.6,
           "conscientiousness": 0.5, "agreeableness": 0.55},
    attachment="anxious", ace=2,
)

async def main():
    runtime = create_runtime(anti_alignment_enabled=True, biological_bridge=bio)
    result = await runtime.orchestrator.process_event(
        provider,
        character_state={
            "name": "林雨",
            "personality": {"openness": 0.6, "neuroticism": 0.75,
                            "attachment_style": "anxious"},
            "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
        },
        event={"description": "陈风两小时没回消息。", "type": "social",
               "significance": 0.6, "participants": [{"name": "陈风", "relation": "partner"}]},
    )
    print(result.combined_analysis)
    print(f"Tokens: {result.total_tokens}")
```

测试：

```bash
# 单元测试
python -m unittest tests.runtime.test_runtime_contract -v

# LLM-as-Judge 基准
python benchmark/real_llm_benchmark.py --provider deepseek --think 1 --bio 1
```

---

## License

MIT
