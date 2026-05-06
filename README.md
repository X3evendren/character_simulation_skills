# Character Simulation Skills

> 不只是让 AI "扮演"角色。是给它一套完整的心理模型，让它像真人一样感受、思考和反应。

---

## 这是什么

一个 Python 库，给 LLM 装上 22 个心理学模型。当你给它一个角色（人格 + 经历 + 当前情境），它会：

1. 用这些模型分析角色的心理状态（人格倾向、情绪、认知偏差、防御机制、社交动态...）
2. 综合所有分析结果
3. 生成角色在这个情境下真实的对话或行为

不是让 LLM "假装"焦虑，而是让它先运行焦虑相关的心理学分析，然后基于分析结果产生行为。

---

## 怎么工作

```
角色设定 + 事件
      │
      ▼
  五层分析管线
  ├─ 第0层: 人格如何影响行为？依恋系统被激活了吗？
  ├─ 第1层: 此刻感受到什么情绪？是否有创伤触发？
  ├─ 第2层: 如何评估这个事件？哪些认知偏差在起作用？用了什么防御？
  ├─ 第3层: 关系中发生了什么？权力动态？对方在想什么？
  ├─ 第4层: 需要反思吗？道德判断？需求层次？
  └─ 第5层: 深层信念被强化还是疗愈？综合一切→生成回应
      │
      ▼
  角色对话/行为
```

每层有多个模型并行运行，层与层之间串行。分析结果逐层传递，最后一层综合所有信息生成角色回应。

---

## 快速开始

```bash
git clone https://github.com/X3evendren/character_simulation_skills.git
cd character_simulation_skills
pip install openai
```

```python
import asyncio
from character_simulation_skills import *

async def main():
    # 1. 注册所有心理学模型
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

    # 2. 连接 LLM (DeepSeek / OpenAI / Ollama 都支持)
    class LLM:
        async def chat(self, messages, temperature, max_tokens):
            # 调用你的 LLM API，返回 OpenAI 格式
            return {
                "choices": [{"message": {"content": '{"key":"value"}'}}],
                "usage": {"total_tokens": 500},
            }

    # 3. 处理事件
    result = await get_orchestrator().process_event(LLM(), {
        "name": "林雨",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.5,
            "extraversion": 0.4, "agreeableness": 0.55, "neuroticism": 0.75,
            "attachment_style": "anxious",
            "defense_style": ["投射"],
            "cognitive_biases": ["灾难化"],
            "moral_stage": 3,
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
    print(f"Token 消耗: {result.total_tokens}")

asyncio.run(main())
```

---

## 心理学模型清单

### 第0层 — 人格

| 模型 | 做什么 |
|------|--------|
| 大五人格 (OCEAN) | 根据开放/尽责/外向/宜人/神经质五项数值，预测角色的行为倾向、情绪反应强度、社交方式 |
| 依恋风格 | 根据安全/焦虑/回避/恐惧-回避四种类型，分析依恋系统激活程度和防御行为 |

### 第1层 — 快速反应

| 模型 | 做什么 |
|------|--------|
| 情绪检测 | 分析 8 种基础情绪（喜/悲/惧/怒/厌/惊/信/期）+ 复合情绪 + 内心与外表的情绪差异 |
| 创伤触发 | 检查当前事件是否触发了角色的创伤记忆 |

### 第2层 — 深度评估

| 模型 | 做什么 |
|------|--------|
| 认知评价 | 评估事件与角色目标的关系（促进/阻碍/无关）及应对能力 |
| 认知偏差 | 检测灾难化、读心术、非黑即白等思维扭曲 |
| 防御机制 | 识别投射、合理化、情感隔离等心理防御 |
| 16维评价 | 从确定性、愉悦度、控制感等 16 个维度全面评估角色对事件的认知 |

### 第3层 — 人际关系

| 模型 | 做什么 |
|------|--------|
| 冲突分析 | 检测批评、防御、蔑视、冷战四种破坏性互动模式 |
| 权力分析 | 分析角色在互动中的权力位置和规训内化 |
| 爱情三角 | 评估亲密、激情、承诺三个维度的强度 |
| 爱情动力学 | 分析双方情感反应的数学动态（谁影响谁、趋向稳定还是震荡）|
| 心理推理 | 推断角色认为对方在想什么、意图是什么、对自己的态度如何 |
| 理想与现实张力 | 角色期望的世界 vs 实际体验的世界之间的落差 |

### 第4层 — 反思

| 模型 | 做什么 |
|------|--------|
| 情绪调节 | 检测角色采用了什么情绪调节策略（压抑、重新评价、分散注意力等）|
| 道德推理 | 判断角色处在哪个道德发展阶段（服从→交换→人际→秩序→契约→原则）|
| 需求层次 | 识别当前主导需求（生存→安全→归属→尊重→自我实现）|
| 动机分析 | 评估自主、胜任、关系三种内在需求的满足状态 |

### 第5层 — 状态更新与回应

| 模型 | 做什么 |
|------|--------|
| 深层信念 | 追踪角色的核心信念（如"我注定被抛弃"）是被当前事件强化还是疗愈 |
| 创伤轨迹 | 评估童年创伤的长期影响轨迹 |
| 回应生成 | **综合以上所有分析 → 生成角色实际对话/行为** |

---

## 测试

| 测试 | 命令 | 说明 |
|------|------|------|
| 技术基准 | `python benchmark/run_benchmark.py` | JSON 解析、字段覆盖、Token 消耗 |
| 心理学验证 | `python tests/validation/run_llm_validation.py --cases 20` | 用真实 LLM 测试 4,500+ 心理学用例 |
| TOCA 演示 | `python tests/validation/toca_demo.py` | 连续意识流演示 |

```bash
export DEEPSEEK_API_KEY="sk-..."
python tests/validation/run_llm_validation.py --cases 20
```

---

## Token 优化

经过系统性的 prompt 精简，每次事件处理的 Token 从 9052 降至 5164（-43%），所有质量指标保持不变。

---

## TOCA：连续意识流（实验性）

当前系统是"事件驱动"的：事件来了→处理→回应。TOCA 是"连续流"模式：

```
同一套分析管线，在不同时间点上同时运行多个实例
实例之间的状态通过一个共享黑板传递
角色不再是"想一下→说一句→等下一个事件"
而是持续在感受、思考、变化
```

已实现核心引擎，处于实验阶段。详见 `core/blackboard.py`, `core/toca_runner.py`。

---

## 部署

| 后端 | 配置 |
|------|------|
| DeepSeek | `export DEEPSEEK_API_KEY="sk-..."` |
| Ollama 本地 | `export LLM_BACKEND=ollama LLM_MODEL=qwen3:14b` |
| OpenAI | `export LLM_BACKEND=openai OPENAI_API_KEY="sk-..."` |

---

## 项目结构

```
core/               — 核心引擎
skills/
  l0_personality/   — 人格模型
  l1_preconscious/  — 快速反应模型
  l2_conscious/     — 深度评估模型
  l3_social/        — 人际关系模型
  l4_reflective/    — 反思模型
  l5_state_update/  — 状态更新 + 回应生成
tests/validation/   — 4,500 条心理学验证用例
benchmark/          — 技术基准
```

---

## 局限

- 每次事件处理调用 15-20 次 LLM，约 5,000 tokens
- 心理分析的准确性取决于底层 LLM 的能力，不同模型差异可能很大
- 当前是事件驱动模式，连续流（TOCA）尚在实验阶段
- 英文情感标签在中英文 LLM 上可能有翻译歧义

## 许可

MIT
