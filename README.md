# Character Simulation Skills

> 为 LLM 赋予结构化心理模型，生成具有真实心理深度的角色行为。

---

## 概述

基于 CLARION 认知架构，将 22 个心理学模型组织为五层处理管线。给定角色的人格画像和情境事件，系统通过分层并行分析——从人格到情绪、从认知偏差到防御机制、从社交动态到道德推理——最终综合所有分析生成角色的对话或行为。

区别于让 LLM "即兴扮演"角色，这里每个行为都由结构化的心理分析驱动，具有可追溯的因果链。

---

## 架构

```
事件/感知
    │
    ▼
  感知过滤 (低显著性缓冲, 高显著性通过)
    │
    ├─ L0 人格 ───── 大五人格 · 依恋风格
    ├─ L1 情绪 ───── 情绪检测 · 创伤触发
    ├─ L2 认知 ───── 认知评价 · 偏差 · 防御 · 16维评价
    ├─ L3 社交 ───── 冲突 · 权力 · 爱情 · 心理推理 · 理想张力
    ├─ L4 反思 ───── 情绪调节 · 道德 · 需求 · 动机
    └─ L5 综合 ───── 图式更新 · 创伤轨迹 · 回应生成
    │
    ▼
  回应 / 行为
```

同层并行，跨层串行。L3 按触发条件激活，L4 仅在关键场景运行。

### 连续流模式 (TOCA)

除事件驱动的批处理外，系统支持连续状态流：

```
同一分析管线，在时间偏移上运行多个实例
间隔 = 推理时间 / 实例数 → 体感连续
实例间通过 Blackboard 共享心理状态（乐观并发, 版本仲裁）
```

内置处理模块：感知过滤、离线巩固、长期记忆桥接、层次化预测、选择性广播、元认知自监控。

---

## 快速开始

```bash
git clone https://github.com/X3evendren/character_mind.git
cd character_mind
pip install openai
```

```python
import asyncio
from character_mind import *

async def main():
    registry = get_registry()
    for cls in [BigFiveSkill, AttachmentSkill,
                PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
                OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill,
                SmithEllsworthSkill,
                GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
                StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
                GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
                YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill]:
        registry.register(cls())

    class LLM:
        async def chat(self, messages, temperature, max_tokens):
            return {
                "choices": [{"message": {"content": '{"key":"value"}'}}],
                "usage": {"total_tokens": 500},
            }

    result = await get_orchestrator().process_event(LLM(), {
        "name": "林雨",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.5,
            "extraversion": 0.4, "agreeableness": 0.55, "neuroticism": 0.75,
            "attachment_style": "anxious", "defense_style": ["投射"],
            "cognitive_biases": ["灾难化"], "moral_stage": 3,
        },
        "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
    }, {
        "description": "陈风两小时没回消息了。",
        "type": "social",
        "participants": [{"name": "陈风", "relation": "partner"}],
        "significance": 0.5,
    })

    print(f"回应: {result.combined_analysis}")
    print(f"Token: {result.total_tokens}")

asyncio.run(main())
```

---

## 心理学模型

### L0 人格
| 模型 | 功能 |
|------|------|
| 大五人格 (OCEAN) | 预测行为倾向、情绪反应强度、社交方式、决策风格 |
| 依恋风格 | 分析安全/焦虑/回避/恐惧-回避四种类型的激活与防御 |

### L1 情绪
| 模型 | 功能 |
|------|------|
| 情绪检测 (Plutchik) | 8种基础情绪 + 复合情绪 + 内外情绪差异 |
| 创伤触发 | 检查事件是否触发创伤记忆，评估侵入/回避/高唤醒风险 |

### L2 认知
| 模型 | 功能 |
|------|------|
| 认知评价 (OCC) | 目标关联/促进/归因/意外性/应对/规范 |
| 认知偏差 | 灾难化、读心术、非黑即白等思维扭曲 |
| 防御机制 | 投射、合理化、情感隔离等层级分析 |
| 16维评价 | 确定性、愉悦度、控制感等多维度认知轮廓 |

### L3 社交
| 模型 | 功能 |
|------|------|
| 冲突分析 (Gottman) | 批评、防御、蔑视、冷战四种破坏模式 |
| 情爱现象学 | 爱欲还原——角色如何体验亲密 |
| 权力分析 | 规训技术、内化凝视、主体化张力 |
| 爱情三角 | 亲密/激情/承诺三维评估 |
| 爱情动力学 | 双方情感反应的数学动态 |
| 心理推理 (ToM) | 推断他人信念、意图、情感 |
| 理想世界张力 | 期望 vs 实际体验的落差 |

### L4 反思
| 模型 | 功能 |
|------|------|
| 情绪调节 (Gross) | 策略检测与效能评估 |
| 道德推理 | 6阶段道德发展判断 |
| 需求层次 | 当前主导需求识别 |
| 动机分析 (SDT) | 自主/胜任/关系三需求状态 |

### L5 综合
| 模型 | 功能 |
|------|------|
| 图式更新 | 核心信念被强化或疗愈 |
| 创伤轨迹 | 童年创伤的长期影响评估 |
| 回应生成 | 综合所有分析 → 角色对话/行为 |

---

## 测试

| 测试 | 命令 | 指标 |
|------|------|------|
| 技术基准 | `python benchmark/run_benchmark.py` | JSON解析、字段覆盖、Token |
| 心理学验证 | `python tests/validation/run_llm_validation.py --cases 20` | DeepSeek 真实LLM, 4,500用例, 总体0.85 |
| Mock回归 | `python tests/validation/run_validation.py` | 快速全管线 |
| TOCA连续流 | `python tests/validation/toca_single_test.py` | 三阶段状态流 |
| 交互式对话 | `python tests/validation/toca_interactive.py` | 实时对话 |

---

## 部署

| 后端 | 配置 |
|------|------|
| DeepSeek | `export DEEPSEEK_API_KEY="sk-..."` |
| Ollama | `export LLM_BACKEND=ollama LLM_MODEL=qwen3:14b` |
| OpenAI | `export LLM_BACKEND=openai OPENAI_API_KEY="sk-..."` |

---

## 项目结构

```
core/                    — 引擎 (编排器, Blackboard, 意识层, 丘脑门控, 离线巩固...)
skills/l0_personality/   — 人格模型
skills/l1_preconscious/  — 情绪模型
skills/l2_conscious/     — 认知模型
skills/l3_social/        — 社交模型
skills/l4_reflective/    — 反思模型
skills/l5_state_update/  — 综合与生成
tests/validation/        — 4,500条心理学验证用例
benchmark/               — 技术基准
docs/superpowers/specs/  — 设计文档
```

---

## 局限

- 每事件调用15-20次LLM，约5,000 tokens（已优化-43%）
- 心理分析准确性取决于底层LLM能力
- 英文情感标签在中英文LLM上有翻译歧义
- TOCA连续流需真实LLM调用，有API延迟

MIT
