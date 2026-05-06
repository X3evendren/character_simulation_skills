# Character Simulation Skills

> 为任何角色赋予真实的心理深度 — 五层认知编排，37 个心理学模型，一次事件处理。

---

## ✨ 核心价值

- 🧠 **完整的心理建模** — 从人格特质到情感反应，从认知偏差到防御机制，覆盖角色心理的每一层
- ⚡ **同层并行，跨层串行** — 基于 CLARION 认知架构，L0-L5 五层编排，`asyncio.gather` 并行执行
- 🔍 **科学依据** — Costa & McCrae, Plutchik, OCC, Gottman, Kohlberg, Maslow 等 37 个经同行评审的心理学模型
- 🛡️ **抗扰动解析** — `extract_json()` 自动修复尾随逗号、单引号、截断、BOM 等 LLM 输出缺陷
- 🗣️ **多 Agent 对话** — 发言者完整认知管线 + 倾听者 `micro_update()` 状态微调

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/X3evendren/character_simulation_skills.git
```

纯 Python 标准库，无外部依赖。

### 最小示例

```python
import asyncio
from character_simulation_skills import (
    get_registry, get_orchestrator,
    BigFiveSkill, AttachmentSkill,
    PlutchikEmotionSkill, PTSDTriggerSkill,
    OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
    GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
    StrogatzSkill, FisherLoveSkill, DiriGentSkill,
    GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
    YoungSchemaSkill, ACETraumaSkill,
)

async def main():
    # 1. 注册所有 Skill
    registry = get_registry()
    for cls in [BigFiveSkill, AttachmentSkill, PlutchikEmotionSkill, PTSDTriggerSkill,
                OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
                GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
                StrogatzSkill, FisherLoveSkill, DiriGentSkill,
                GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
                YoungSchemaSkill, ACETraumaSkill]:
        registry.register(cls())

    # 2. 实现 Provider (你的 LLM 客户端)
    class LLM:
        async def chat(self, messages, temperature, max_tokens):
            return {  # OpenAI 格式
                "choices": [{"message": {"content": '{"key":"value"}'}}],
                "usage": {"total_tokens": 500},
            }

    # 3. 处理事件
    result = await get_orchestrator().process_event(
        LLM(),
        character_state={  # 角色心理画像
            "name": "林雨",
            "personality": {
                "openness": 0.6, "conscientiousness": 0.5,
                "extraversion": 0.4, "agreeableness": 0.55, "neuroticism": 0.65,
                "attachment_style": "anxious",
                "defense_style": ["投射", "合理化"],
                "moral_stage": 3,
            },
            "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
            "ideal_world": {"ideal_self": "被坚定选择的人"},
            "motivation": {"current_goal": "确认对方的感情"},
        },
        event={
            "description": "陈风两小时没回消息了。",
            "type": "social",
            "participants": [{"name": "陈风", "relation": "partner"}],
            "significance": 0.5,
        },
    )
    print(f"Token: {result.total_tokens} | 错误: {len(result.errors)}")

asyncio.run(main())
```

## 🏗️ 架构

### 五层认知管线

```
 Event
   │
   ▼
[预处理] 情感衰减 · 记忆检索 · 人格状态转移
   │
   ├─ L0 人格滤镜 ─────────────── big_five · attachment │ always │
   ├─ L1 快速前意识 ───────────── plutchik · ptsd_trigger │ always │
   ├─ L2 意识层评估 ───────────── occ · bias · defense · smith │ always │
   ├─ L3 关系/社会 ────────────── gottman · foucault · sternberg … │ 按触发 │
   ├─ L4 反思处理 ─────────────── gross · kohlberg · maslow · sdt │ 关键场景 │
   └─ L5 状态更新 ─────────────── young_schema · ace_trauma │ 串行 │
   │
   ▼
[持久化] 情感残留 · 事件记忆 · 状态写回
```

### 核心组件

| 模块 | 职责 |
|------|------|
| `base.py` | `BaseSkill` 基类 · `SkillResult` 数据结构 · `extract_json()` 抗扰动解析 |
| `orchestrator.py` | `CognitiveOrchestrator` 五层编排器 · `process_event()` · `process_multi_agent_turn()` |
| `registry.py` | `SkillRegistry` 注册/发现 · 按层/域/触发条件检索 |
| `emotion_decay.py` | `EmotionDecayModel` PAD 双速衰减 · 快速 2 事件半衰 / 慢速 50 事件半衰 |
| `episodic_memory.py` | `EpisodicMemoryStore` 情感签名事件记忆 · 容量 100 条 |
| `personality_state_machine.py` | 8 种情境人格状态 · 由事件类型 + 情绪驱动转移 |
| `emotion_vocabulary.py` | 40+ 细粒度情感 · 16 种复合情感 · 8 种功能性情感 |
| `conversation_history.py` | `ConversationHistoryStore` 外置对话记忆 · 不进入 LLM 上下文窗口 |

## 📦 Skill 分层清单

### L0 — 人格滤镜

| Skill | 模型 | 星级 |
|-------|------|------|
| `big_five_analysis` | Costa & McCrae (1992) OCEAN | ⭐⭐⭐⭐⭐ |
| `attachment_style_analysis` | Bowlby / Ainsworth 依恋理论 | ⭐⭐⭐⭐⭐ |

### L1 — 快速前意识

| Skill | 模型 | 星级 |
|-------|------|------|
| `plutchik_emotion` | Plutchik (1980) 情感轮 — 8 维 + 复合 | ⭐⭐⭐⭐ |
| `ptsd_trigger_check` | PTSD 创伤触发与侵入风险 | ⭐⭐⭐⭐ |

### L2 — 意识层评估

| Skill | 模型 | 星级 |
|-------|------|------|
| `occ_emotion_appraisal` | Ortony, Clore & Collins (1988) | ⭐⭐⭐⭐⭐ |
| `cognitive_bias_detect` | Kahneman & Tversky 认知偏差 | ⭐⭐⭐⭐⭐ |
| `defense_mechanism_analysis` | Anna Freud / Vaillant 防御层级 | ⭐⭐⭐⭐ |
| `smith_ellsworth_appraisal` | Smith & Ellsworth (1985) 16 维评价 | ⭐⭐⭐⭐ |

### L3 — 关系/社会

| Skill | 模型 | 触发 |
|-------|------|------|
| `gottman_interaction` | Gottman 方法 · 四骑士 + 魔法比例 | romantic · conflict |
| `marion_erotic_phenomenology` | 马里翁情爱现象学 | romantic |
| `foucauldian_power_analysis` | 福柯权力分析 | authority · social |
| `sternberg_triangle` | Sternberg 爱情三角 | romantic |
| `strogatz_love_dynamics` | Strogatz Romeo-Juliet 动力学 | romantic |
| `fisher_love_stages` | Fisher 三阶段 · 神经化学 | romantic |
| `dirigent_world_tension` | DiriGent 理想世界张力 | reflective |

### L4 — 反思处理

| Skill | 模型 | 触发 |
|-------|------|------|
| `gross_emotion_regulation` | Gross 情绪调节策略 | reflective |
| `kohlberg_moral_reasoning` | Kohlberg 道德推理阶段 | moral |
| `maslow_need_stack` | Maslow 需求层次 | reflective |
| `sdt_motivation_analysis` | SDT 自我决定理论 | reflective |

### L5 — 状态更新

| Skill | 模型 |
|-------|------|
| `young_schema_update` | Young 图式疗法 |
| `ace_trauma_processing` | ACE 童年创伤影响 |

## 🧩 关键概念

| 概念 | 说明 |
|------|------|
| **情感衰减** | PAD 三维连续情感 · 事件结束后情感不归零 · 双速半衰期 |
| **事件记忆** | 情感签名 + 显著性阈值 · 100 条容量 · 按时间/相似度/标签检索 |
| **人格状态机** | OCEAN 基线 + 8 种情境状态 · 事件类型 + 情绪驱动转移 |
| **反 RLHF 偏差** | 沉默法则 — 正面定义行为范围 · 不输出"不要 X" |
| **SPASM 投射** | 第一人称视角重新解释共享事件 · 不标注角色标签 |
| **多 Agent 对话** | 发言者完整管线 · 倾听者 `micro_update()` |

## 🔧 Provider 接口

```python
class YourLLM:
    async def chat(
        self,
        messages: list[dict],       # [{"role": "user", "content": "..."}]
        temperature: float = 0.3,   # 低温，分析任务
        max_tokens: int = 500,      # 最大输出
    ) -> dict:
        return {
            "choices": [{"message": {"content": "JSON 字符串"}}],
            "usage": {"total_tokens": 1234},
        }
```

## 🐳 部署指南

### 支持的 LLM 后端

| 后端 | 环境变量 | 说明 |
|------|---------|------|
| DeepSeek (默认) | `DEEPSEEK_API_KEY=sk-...` | OpenAI 兼容，快且便宜 |
| Ollama 本地 | `LLM_BACKEND=ollama` | 免费，需本地 GPU |
| OpenAI | `LLM_BACKEND=openai` `OPENAI_API_KEY=sk-...` | 标准 API |

### 运行方式

```bash
# 1. 克隆
git clone https://github.com/X3evendren/character_simulation_skills.git
cd character_simulation_skills

# 2. 安装依赖
pip install openai  # 仅 API 后端需要

# 3. 设置 API Key (选一个)
export DEEPSEEK_API_KEY="sk-..."

# 4. 运行验证
python tests/validation/run_llm_validation.py --cases 10

# 5. 运行技术基准
python benchmark/run_benchmark.py --quality 0.35 --scenarios 0
```

## 🧪 测试

### 三层测试体系

| 层 | 命令 | 测什么 |
|----|------|--------|
| 技术基准 | `python benchmark/run_benchmark.py` | JSON 解析率、字段覆盖率、Token 消耗 |
| 心理学验证 | `python tests/validation/run_llm_validation.py --cases 20` | 真实 LLM 心理学准确性 (4,500+ 用例) |
| Mock 验证 | `python tests/validation/run_validation.py` | 快速回归测试 (Mock LLM) |

### 添加新 Skill

1. 在 `skills/lX_xxx/` 下创建新文件，继承 `BaseSkill`：

```python
from ...core.base import BaseSkill, SkillMeta

class MyNewSkill(BaseSkill):
    meta = SkillMeta(
        name="my_new_skill",
        domain="psychology",
        layer=2,
        description="分析角色的...",
        scientific_basis="Paper (Year)",
        scientific_rating=4,
        trigger_conditions=["always"],
        estimated_tokens=400,
    )

    def build_prompt(self, character_state, event, context):
        return f"..."  # 构建分析 prompt

    def parse_output(self, raw_output):
        from ...core.base import extract_json
        result = extract_json(raw_output)
        return result if result else {"key": "default"}
```

2. 在 `skills/lX_xxx/__init__.py` 中导出
3. 在 `__init__.py` 中导入
4. 在 `core/orchestrator.py` 的对应层添加 skill 名称
5. 在 `benchmark/run_benchmark.py` 和 `tests/validation/validator.py` 中注册
6. 在 `tests/validation/fixtures/` 中添加验证用例

### 项目结构

```
core/               — 基础设施 (8 模块)
skills/
  l0_personality/   — 人格滤镜 (OCEAN, 依恋)
  l1_preconscious/  — 快速前意识 (Plutchik, PTSD, 情感探针)
  l2_conscious/     — 意识层评估 (OCC, 偏差, 防御, Smith-Ellsworth)
  l3_social/        — 关系/社会 (Gottman, 福柯, ToM 等 8 个)
  l4_reflective/    — 反思处理 (Gross, Kohlberg, Maslow, SDT)
  l5_state_update/  — 状态更新 (图式, ACE, 回应生成)
tests/validation/   — 4,500 条心理学验证用例
benchmark/          — 技术基准
docs/superpowers/specs/ — 设计文档 (含 TOCA 连续状态流架构)
```

## 📄 许可

MIT
