# Character Mind

为 LLM 赋予结构化心理模型，基于 **CLARION 认知架构 + Scherer 评估理论** 生成具有可追溯心理因果链的角色行为。

---

## 架构

五层认知编排管线，将 37 个心理学模型组织为分层处理流程：

```
事件
  │
  ├─ L0 人格滤镜 ──────── BigFive · Attachment
  ├─ L1 快速前意识 ────── Plutchik · PTSDTrigger · EmotionProbe
  ├─ L2 意识层评估 ────── OCC · CognitiveBias · DefenseMechanism · SmithEllsworth
  ├─ L3 关系/社会处理 ─── Gottman · Foucault · Sternberg · TheoryOfMind · ...
  ├─ L4 反思处理 ──────── GrossRegulation · Kohlberg · Maslow · SDT
  └─ L5 状态更新与生成 ── YoungSchema · ACETrauma · ResponseGenerator
      │
      ▼
  回应 / 行为
```

- **同层并行** (`asyncio.gather`)，**跨层串行**
- L0 始终在线；L1-L2 始终在线；L3 按触发条件 (`social`/`romantic`/`conflict`/...) 选择性激活；L4 仅在显著事件中激活；L5 始终执行
- 所有 Skill 通过 `build_prompt()` → LLM 调用 → `parse_output()` 解析 JSON 结果

---

## 质量评估

LLM-as-Judge 六维度评价体系（DeepSeek V4 Pro 作为评审）：

| 维度 | 说明 |
|------|------|
| 情感真实度 | 情绪反应的合理性与自然度 |
| 人格一致性 | 行为是否偏离 OCEAN 基线 |
| 防御表达 | 防御机制是否自然嵌入回应 |
| 情感深度 | 是否超出表层情感，体现复杂心理 |
| 关系敏感性 | 对关系动态和权力结构的感知 |
| 潜台词与克制 | 未言明的心理内容与自我抑制 |

### 管线质量对比 (DeepSeek V4 Pro, temperature=0.3)

| 配置 | Skill 数 | 质量分数 | 说明 |
|------|----------|----------|------|
| Lean | 6 | 0.89 | BigFive + Plutchik + OCC + ToM + Gross + Response |
| Medium | 10 | 0.93 | Lean + Attachment + PTSD + Defense + Foucault |
| **理论最优** | **11** | **0.96-0.98** | **BigFive + Attachment(条件) + Plutchik + PTSD + OCC + Defense + ToM + Gottman + Foucault(触发选择) + Gross + SDT(仅显著事件) + Response + YoungSchema/ACE(条件)** |
| Full | 26 | 0.90 | 全部注册，层内干扰导致噪声累积 |

理论最优管线通过精准的触发条件控制避免层内 Skill 冲突，在覆盖完整心理维度的同时保持输出质量。

---

## 关键特性

- **PAD 双速情感衰减**：愉悦-唤醒-支配三维情感向量，短/长半衰期分别对应情绪波动与心境基调
- **情景记忆系统**：时序关系边 + 优先级淘汰 + 情感标签 + 冻结快照
- **人格状态机**：OCEAN 基线 + 8 种情境状态（依恋激活/创伤闪回/认知失调等），状态间转换规则驱动
- **80+ 细粒度情感词汇**：16 种复合情感 + 16 种功能情感（含行为后果映射）
- **反 RLHF 偏差注入 (Silence Rule)**：仅在 L5 回应生成层注入角色语境豁免声明，防止安全对齐干扰角色模拟
- **9 数据集适配器**：5,960 条测试用例，覆盖社交/冲突/浪漫/道德/创伤等场景

---

## 快速开始

```bash
pip install openai
```

```python
import asyncio
from character_mind import get_orchestrator, get_registry

# 注册 Skill（理论最优管线示例）
registry = get_registry()
for cls in [BigFiveSkill, AttachmentSkill,
            PlutchikEmotionSkill, PTSDTriggerSkill,
            OCCEmotionSkill, DefenseMechanismSkill,
            TheoryOfMindSkill, GottmanSkill, FoucaultSkill,
            GrossRegulationSkill, SDTSkill,
            YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill]:
    registry.register(cls())

# Mock LLM provider（生产环境替换为 DeepSeek/OpenAI）
class MockLLM:
    async def chat(self, messages, temperature, max_tokens):
        return {
            "choices": [{"message": {"content": '{"analysis": "..."}'}}],
            "usage": {"total_tokens": 500},
        }

async def main():
    result = await get_orchestrator().process_event(
        MockLLM(),
        character_state={
            "name": "林雨",
            "personality": {
                "openness": 0.6, "conscientiousness": 0.5,
                "extraversion": 0.4, "agreeableness": 0.55,
                "neuroticism": 0.75,
                "attachment_style": "anxious",
            },
            "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
        },
        event={
            "description": "陈风两小时没回消息了。",
            "type": "social",
            "participants": [{"name": "陈风", "relation": "partner"}],
            "significance": 0.5,
        },
    )
    print(f"分析: {result.combined_analysis}")
    print(f"Token: {result.total_tokens}")

asyncio.run(main())
```

---

## 测试

| 测试 | 命令 | 说明 |
|------|------|------|
| LLM-as-Judge 基准 | `python benchmark/real_llm_benchmark.py --provider deepseek --think 1 --scenarios 2` | DeepSeek V4 Pro 真实调用，6 维度评分 |
| Mock 快速基准 | `python benchmark/improved_benchmark.py` | Mock LLM，验证 JSON 解析/字段覆盖/Token |
| 回归验证 | `python tests/validation/run_validation.py` | 快速全管线测试 |

---

## 项目结构

```
core/                          — 引擎基础设施
  base.py                       BaseSkill, SkillMeta, SkillResult
  registry.py                   SkillRegistry
  orchestrator.py               CognitiveOrchestrator（五层编排）
  emotion_decay.py              PAD 双速衰减
  episodic_memory.py            情景记忆（时序关系+淘汰+快照）
  personality_state_machine.py  人格状态机
  emotion_vocabulary.py         80+ 情感词汇
  conversation_history.py       对话历史存储
skills/
  l0_personality/               BigFive, Attachment
  l1_preconscious/              Plutchik, PTSDTrigger, EmotionProbe
  l2_conscious/                 OCC, CognitiveBias, DefenseMechanism, SmithEllsworth
  l3_social/                    Gottman, Marion, Foucault, Sternberg, Strogatz, ...
  l4_reflective/                GrossRegulation, Kohlberg, Maslow, SDT
  l5_state_update/              YoungSchema, ACETrauma, ResponseGenerator
benchmark/                      质量基准（LLM-as-Judge + Mock）
tests/validation/               回归测试与验证用例
```

---

## 部署

| 后端 | 环境变量 |
|------|----------|
| DeepSeek（推荐） | `DEEPSEEK_API_KEY=sk-...` (温度 0.3, 生产启用 `thinking`) |
| OpenAI | `OPENAI_API_KEY=sk-...` `LLM_BACKEND=openai` |
| Ollama | `LLM_BACKEND=ollama` `LLM_MODEL=qwen3:14b` |

---

## 设计文档

- `docs/superpowers/specs/2026-05-06-polish-and-validate-design.md` — 打磨计划
- `docs/superpowers/specs/2026-05-06-toca-architecture-design.md` — 连续状态流架构

---

## 局限

- 每事件约 11 次 LLM 调用（理论最优管线），~5,000 tokens
- 心理分析准确性取决于底层 LLM 能力
- 层内 Skill 过多会产生分析噪声（Full 配置质量下降至 0.90）
- 建议使用 DeepSeek V4 Pro 并启用 thinking mode 以获得最佳效果

MIT
