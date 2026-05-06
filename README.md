# Character Simulation Skills

> **不只是让 LLM "扮演"角色。是给 LLM 一套完整的心智。**
>
> 基于 CLARION 认知架构 + Scherer 评估理论 + 现象学传统，22 个心理学模型通过五层时序编排器协同工作，将角色的心理状态从"人格标签"推进为连续的意识流。

---

## 🎯 为什么这样设计

现有的 LLM 角色扮演系统都有一个共同的问题：**角色的心理是扁平的**。一句 system prompt 定义人格，然后 LLM 即兴发挥。没有记忆的连续性，没有情感的内外差异，没有防御机制的运作——角色只是"装作"有心理深度。

我们走了另一条路。**不是让 LLM 假装有心理活动，而是构建一个结构化的认知管道，让 LLM 在每一步都基于真实的心理学模型进行分析，然后从分析中产生行为。**

```
其他系统: System prompt "你是一个焦虑的人" → LLM 即兴发挥

我们的系统:
  角色心理画像 → [22个心理学模型分层分析] → 综合 → 角色行为
                ↑                           ↑
           每个模型有科学依据              分析驱动行为，不是模仿
```

### 三个设计决策

**1. CLARION 认知架构**（Ron Sun, 2006）
人类认知不是单层处理。CLARION 区分了隐式认知（快速、自动、情感驱动）和显式认知（缓慢、审慎、规则驱动）。我们的 L1（前意识）模拟隐式层，L2-L4 模拟显式层。同层并行、跨层串行的编排方式直接来自 CLARION 的隐式-显式交互模型。

**2. 现象学传统**（Marion 情爱现象学 + Foucault 权力分析）
大多数"角色扮演"系统只关注人格特质。我们加入了现象学维度——角色如何**体验**自己的存在？马里翁的"爱欲还原"（有人爱我吗→我的存在对谁有好处→我能先去爱吗）提供了一套超越简单"情感标签"的分析框架。福柯的权力分析让角色在权威结构中的主体化过程变得可计算。

**3. 从分析到生成的闭环**
学术界的心理学 LLM 系统（如 PsyMem、MetaMind）止步于分析。我们加入了一个回应生成器，它不"扮演"角色，而是**读取所有层的分析结果**，基于人格偏置+当前情绪+防御状态+关系动态综合产生行为。回应不是凭空想象的，是有心理因果链的。

---

## 🏗️ 架构

```
感知/事件
    │
    ▼
[预处理] 情感衰减 · 记忆检索 · 人格状态机更新
    │
    ├─ L0 人格滤镜 ───────── big_five · attachment │ 始终在线 │
    ├─ L1 前意识 ─────────── plutchik · ptsd · emotion_probe │ 始终在线 │
    ├─ L2 意识层评估 ─────── occ · bias · defense · smith │ 始终在线 │
    ├─ L3 关系/社会 ──────── gottman · marion · foucault · sternberg · ToM … │ 按触发 │
    ├─ L4 反思处理 ───────── gross · kohlberg · maslow · sdt │ 关键场景 │
    └─ L5 状态更新 + 回应 ── young_schema · ace_trauma · response_generator │ 串行 │
    │
    ▼
[持久化] 情感残留 · 事件记忆 · 人格状态写回
```

### 各层职责

| 层 | 做什么 | 什么时候 |
|----|--------|---------|
| **L0 人格** | 基于 OCEAN 数值预测行为偏置；检测依恋系统激活水平 | 每次 |
| **L1 前意识** | 快速情绪检测（Plutchik 8 维+复合）；PTSD 触发扫描；隐式情感探针 | 每次 |
| **L2 意识评估** | OCC 认知评估；认知偏差识别；防御机制分析；Smith-Ellsworth 16 维评价 | 每次 |
| **L3 关系社会** | Gottman 冲突模式；情爱现象学；权力动态；爱情三角/动力学；ToM 推理 | 按触发条件 |
| **L4 反思** | 情绪调节策略；道德推理阶段；需求层次；自我决定动机 | 仅关键场景 |
| **L5 状态+回应** | 图式强化/疗愈；ACE 创伤轨迹；**综合所有分析 → 角色对话/行为** | 每次 |

### L5 为什么是"状态更新"

L1 的 `ptsd_trigger_check` 回答"这个事件触发了创伤反应吗？"（即时，前意识）  
L5 的 `ace_trauma_processing` 回答"这个事件对创伤系统的**长期轨迹**有什么影响？"（累积，状态变化）

L2 的 `defense_mechanism_analysis` 回答"这个事件激活了什么防御？"（即时）  
L5 的 `young_schema_update` 回答"这个事件让防御背后的深层图式**变得更坚固还是更松动**？"（累积）

即时检测 vs 长期轨迹——这是 L1-L4 与 L5 的本质区别。

---

## 🚀 快速开始

```bash
git clone https://github.com/X3evendren/character_simulation_skills.git
cd character_simulation_skills
pip install openai  # 仅 API 后端需要
```

```python
import asyncio
from character_simulation_skills import (
    get_registry, get_orchestrator,
    BigFiveSkill, AttachmentSkill,
    PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
    OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
    GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
    StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
    GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
    YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
)

async def main():
    # 注册技能
    registry = get_registry()
    for cls in [BigFiveSkill, AttachmentSkill,
                PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
                OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
                GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
                StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
                GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
                YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill]:
        registry.register(cls())

    # 你的 LLM 客户端 (OpenAI 兼容接口)
    class LLM:
        async def chat(self, messages, temperature, max_tokens):
            # 调用 DeepSeek / OpenAI / Ollama ...
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
        "ideal_world": {"ideal_self": "被坚定选择的人"},
        "motivation": {"current_goal": ""},
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

## 📊 验证结果

### DeepSeek-chat 真实 LLM 验证（30 用例分层抽样）

| 维度 | 得分 | 说明 |
|------|------|------|
| L5 回应生成 | **1.000** | 角色对话始终产出 |
| L2 认知偏差 | **1.000** | 灾难化/读心术检测准确 |
| L2 防御机制 | **1.000** | 修复后（原 0.00） |
| L4 情绪调节 | **1.000** | Gross 策略检测稳定 |
| L0 依恋 | 0.889 | 安全/焦虑/回避区分良好 |
| L0 大五人格 | 0.714 | 行为偏置预测合理 |
| L1 Plutchik | 0.667 | 情感标签需同义词扩展 |
| L4 Kohlberg | 0.735 | 道德阶段判断基本正确 |
| **总体** | **0.854** | |

### 多 Agent 对话（焦虑型 vs 回避型）

```
林雨 (焦虑): "盯着屏幕想了很久...你在忙吗？"
陈风 (回避): "没什么。你想多了，早点休息吧。"
```

两人反应均符合依恋风格预测。焦虑型寻求确认但不直接表达需求，回避型用距离和理性化保护自己。

### Mock 技术基准

| 指标 | 得分 |
|------|------|
| JSON 解析成功率 | 1.000 |
| 字段覆盖率 | 1.000 |
| 总 Token (8 场景) | ~9,000 |

---

## 🧪 测试体系

| 层 | 命令 | 测什么 |
|----|------|--------|
| **心理学真值** | `python tests/validation/run_llm_validation.py --cases 20` | 真实 LLM 心理学准确性 |
| **技术基准** | `python benchmark/run_benchmark.py` | JSON 解析、字段覆盖、Token |
| **快速回归** | `python tests/validation/run_validation.py` | Mock LLM 全管线 |
| **TOCA 演示** | `python tests/validation/toca_demo.py` | 连续状态流 |

```bash
export DEEPSEEK_API_KEY="sk-..."
python tests/validation/run_llm_validation.py --cases 20
```

---

## 🔮 TOCA：连续状态流（实验性）

当前架构是离散事件批处理。TOCA (Temporal Overlay Cognitive Architecture) 是其连续流扩展：

```
同一五层管道，在时间偏移上运行多个实例
间隔 = 推理时间 / 实例数 → 体感连续

t=0: [实例1: L0──L5] ────────────→ 写入 Blackboard
t=6:      [实例2: L0──L5] ────────────→ 写入 Blackboard
t=12:          [实例3: L0──L5] ────────────→ 写入 Blackboard

每个实例读取 Blackboard 最新状态 + 感知窗口
不等待、不锁死、版本号仲裁
```

已实现：`core/blackboard.py` · `core/perception_stream.py` · `core/toca_runner.py`  
设计文档：`docs/superpowers/specs/2026-05-06-toca-architecture-design.md`

---

## 🐳 部署

| 后端 | 配置 |
|------|------|
| DeepSeek | `export DEEPSEEK_API_KEY="sk-..."` |
| Ollama 本地 | `export LLM_BACKEND=ollama LLM_MODEL=qwen3:14b` |
| OpenAI | `export LLM_BACKEND=openai OPENAI_API_KEY="sk-..."` |

---

## 📁 项目结构

```
core/               — 基础设施 (base, orchestrator, registry, blackboard…)
skills/
  l0_personality/   — OCEAN 人格, 依恋
  l1_preconscious/  — Plutchik 情感, PTSD, 情感探针
  l2_conscious/     — OCC 评估, 认知偏差, 防御机制, Smith-Ellsworth
  l3_social/        — Gottman, 情爱现象学, 福柯权力, ToM 等 8 个
  l4_reflective/    — 情绪调节, 道德推理, 需求层次, SDT
  l5_state_update/  — 图式疗法, ACE 创伤, 回应生成
tests/validation/   — 4,500 条心理学验证用例
benchmark/          — 技术基准
docs/superpowers/specs/ — 设计文档
```

---

## ⚠️ 已知局限

- **不是 AGI**。这个系统模拟心理过程，但不具备真正的意识或感受
- **LLM 依赖**。心理分析的准确性受限于底层 LLM 的能力。不同 LLM 对同一心理维度的判断可能有显著差异
- **Token 成本**。每次事件处理调用 15-22 次 LLM（每个 Skill 一次），约消耗 15K-20K tokens
- **连续流未完成**。TOCA 已实现核心引擎但尚未与现有 Skill 管线完全集成
- **评估天花板**。Mock 验证已达满分（JSON 解析/字段覆盖），但真实 LLM 的心理准确性验证是开放问题——我们是在用心理学理论作为 ground truth，理论本身有局限性
- **英文情感标签偏差**。Plutchik/OCC 的英文情感术语在中文 LLM 上存在翻译歧义

---

## 📄 许可

MIT

---

## 📚 参考文献

- Sun, R. (2025). *Enhancing Computational Cognitive Architectures with LLMs: A Case Study*. arXiv:2509.10972
- Sun, R. (2006). *The CLARION Cognitive Architecture*. Cambridge University Press
- Scherer, K. R. (2001). Appraisal Considered as a Process of Multilevel Sequential Checking
- Marion, J-L. (2003). *Le phénomène érotique*
- Costa & McCrae (1992). NEO PI-R Professional Manual
- Plutchik, R. (1980). *Emotion: A Psychoevolutionary Synthesis*
- Gottman, J. M. (1994). *What Predicts Divorce?*
- Kohlberg, L. (1981). *The Philosophy of Moral Development*
