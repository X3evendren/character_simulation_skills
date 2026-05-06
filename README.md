# Character Mind

为 LLM 赋予结构化心理模型，生成具有可追溯心理因果链的角色行为。基于 CLARION 认知架构，37 个心理学模型以 Skill 形式注册，通过五层时序编排器分层并行处理。

---

## 架构

```
事件 → [L-3 生物驱力] → [L-2 HPA/递质] → [L-1 主动推理]
    → L0 人格滤镜 → L1 前意识 → L2 评价 → L3 社交 → L4 反思 → L5 回应
```

**五层认知管道：**

| 层 | 功能 | 活跃技能 | 触发 |
|----|------|---------|------|
| L0 | 人格滤镜 | BigFive, Attachment | always / social |
| L1 | 快速前意识 | Plutchik, PTSDTrigger | always / trauma |
| L2 | 意识层评估 | OCC, DefenseMechanism | always |
| L3 | 关系/社会处理 | TheoryOfMind, Gottman, Foucault | social/romantic/conflict/authority |
| L4 | 反思处理 | GrossRegulation, SDT | significance >= 0.7 |
| L5 | 状态更新与回应 | ResponseGenerator, YoungSchema, ACETrauma | always / trauma |

**生物基础层（新增）：**

| 层 | 功能 | 核心模型 |
|----|------|---------|
| L-3 | 稳态驱力 | 15 驱力系统（Tyrrell 分层 + Panksepp SEEKING/PLAY/PANIC），W-Learning 行动选择 |
| L-2b | HPA 轴 | CRH→ACTH→CORT→GR 完整 ODE（Sriram 2012），ACE 参数化 |
| L-2a | 神经递质引擎 | DA/5-HT/NE/CORT/OXT，OCEAN→基线映射，受体适应，跨递质交互 |
| L-1 | 主动推理桥接 | 精度加权，预期自由能，信念更新，驱力→行动倾向 |

- **同层并行** (`asyncio.gather`)，**跨层串行**
- 生物层在事件前后自动更新，CORT 调节情绪衰减半衰期，驱力状态注入行为约束

---

## 质量评估

LLM-as-Judge 七维度评价（DeepSeek V4 Pro thinking mode）：

| 维度 | 评估内容 |
|------|---------|
| 情感真实性 | 回应是否自然逼真，无模板痕迹 |
| 人格一致性 | 是否精确体现 OCEAN + 依恋风格 |
| 防御表达 | 防御机制（投射/合理化/理智化）是否自然嵌入 |
| 情感深度 | 是否有复合情感、内在矛盾、"冰山之下"的内容 |
| 关系敏感性 | 对不同关系对象的回应是否有差异 |
| 潜台词与克制 | 弦外之音是否含蓄有力，不翻译成明台词 |
| **心理矛盾性** | 是否呈现不可调和的多重状态，矛盾作为真实人性的一部分 |

### 配置对比 (DeepSeek V4 Pro, 2 scenarios)

| 配置 | Skills | 质量 | Tokens | 说明 |
|------|--------|------|--------|------|
| Lean | 6 | 0.89 | 4,356 | 最小集 |
| Medium | 10 | 0.93 | 7,595 | 每维度一个框架 |
| Full | 26 | 0.90 | 14,470 | 框架噪音导致退化 |
| **最优 + Bio** | **11** | **0.98** | **8,111** | **理论最优 + 生物基础层** |

生物基础层提供 +7.7% 质量提升（0.91→0.98），仅 +4% token 开销。

---

## 关键特性

- **生物基础层**：15 驱力内稳态 + HPA 轴 ODE + 5 递质引擎 + 主动推理桥接
- **OCEAN→神经递质映射**：人格特质自动转化为 DA/5-HT/NE/OXT 基线水平
- **CORT→情绪衰减调制**：高皮质醇延长情绪半衰期，产生更持久的负面情绪
- **开放性条件反RLHF提示**：高 O 角色允许自我反思，低 O 角色保持行为约束
- **PAD 双速情感衰减**：快速层（2 事件半衰）与慢速层（50 事件半衰）
- **情景记忆系统**：时序关系边 + 优先级淘汰 + 情感标签 + 冻结快照
- **人格状态机**：OCEAN 基线 + 8 种情境状态 + 逐轮微调
- **80+ 细粒度情感词汇**：16 复合情感 + 16 功能情感（含行为后果映射）
- **9 数据集适配器**：5,960 条测试用例

---

## 快速开始

```bash
pip install openai
```

```python
import asyncio
from character_mind import get_orchestrator, get_registry
from character_mind.core.biological import BiologicalBridge

# 注册最优管线 Skill
registry = get_registry()
for cls in [BigFiveSkill, AttachmentSkill,
            PlutchikEmotionSkill, PTSDTriggerSkill,
            OCCEmotionSkill, DefenseMechanismSkill,
            TheoryOfMindSkill, GottmanSkill, FoucaultSkill,
            GrossRegulationSkill, SDTSkill,
            YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill]:
    registry.register(cls())

# 生物基础层
bio = BiologicalBridge()
bio.set_character_profile(
    ocean={"extraversion": 0.4, "neuroticism": 0.75, "openness": 0.6,
           "conscientiousness": 0.5, "agreeableness": 0.55},
    attachment="anxious", ace=2,
)

# 创建编排器并绑定生物层
orch = get_orchestrator(anti_alignment_enabled=True, biological_bridge=bio)

async def main():
    result = await orch.process_event(
        provider,  # DeepSeek/OpenAI/Ollama provider
        character_state={
            "name": "林雨",
            "personality": {"openness": 0.6, "conscientiousness": 0.5,
                            "extraversion": 0.4, "agreeableness": 0.55,
                            "neuroticism": 0.75, "attachment_style": "anxious"},
            "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
        },
        event={"description": "陈风两小时没回消息", "type": "social",
               "participants": [{"name": "陈风", "relation": "partner"}],
               "significance": 0.5},
    )
    print(result.combined_analysis)
```

---

## 测试

| 测试 | 命令 | 说明 |
|------|------|------|
| LLM-as-Judge | `python benchmark/real_llm_benchmark.py --provider deepseek --think 1 --bio 1 --scenarios 2` | DeepSeek V4 Pro，7 维度评分 |
| Mock 快速 | `python benchmark/improved_benchmark.py` | Mock LLM，验证指标 |
| 回归验证 | `python tests/validation/run_validation.py` | 5,960 用例验证 |

---

## 项目结构

```
core/
  biological/                   — 生物基础层 (新增)
    biological_state.py           统一状态容器
    drive_system.py               L-3: 15 驱力 + W-Learning
    hpa_axis.py                   L-2b: HPA 轴 ODE
    neurotransmitter.py           L-2a: 5 递质引擎
    active_inference.py           L-1: 主动推理桥接
    biological_bridge.py          集成适配器
  base.py                       BaseSkill, SkillMeta, SkillResult
  orchestrator.py               CognitiveOrchestrator
  emotion_decay.py              PAD 双速衰减 (CORT 调制)
  registry.py                   SkillRegistry
  episodic_memory.py            情景记忆
  personality_state_machine.py  人格状态机
  emotion_vocabulary.py         80+ 情感词汇
skills/
  l0_personality/               BigFive, Attachment
  l1_preconscious/              Plutchik, PTSDTrigger
  l2_conscious/                 OCC, DefenseMechanism
  l3_social/                    TheoryOfMind, Gottman, Foucault
  l4_reflective/                GrossRegulation, SDT
  l5_state_update/              ResponseGenerator, YoungSchema, ACETrauma
benchmark/
  real_llm_benchmark.py          LLM-as-Judge 基准
  improved_benchmark.py          Mock 快速基准
tests/validation/                回归测试 (5,960 用例)
docs/superpowers/specs/          设计文档
```

---

## 部署

| 后端 | 环境变量 |
|------|----------|
| DeepSeek（推荐） | `DEEPSEEK_API_KEY=sk-...` |
| OpenAI | `OPENAI_API_KEY=sk-...` `LLM_BACKEND=openai` |
| Ollama | `LLM_BACKEND=ollama` `LLM_MODEL=qwen3:14b` |

推荐使用 DeepSeek V4 Pro 并启用 thinking mode 获得最佳质量。

---

## 设计文档

- `docs/superpowers/specs/2026-05-07-biological-foundation-design.md` — 生物基础层设计
- `docs/superpowers/specs/2026-05-06-polish-and-validate-design.md` — 打磨计划
- `docs/superpowers/specs/2026-05-06-toca-architecture-design.md` — 连续状态流架构

---

MIT
