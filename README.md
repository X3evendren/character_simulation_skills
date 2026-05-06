# Character Simulation Skills — 五层认知编排系统

基于 **CLARION 认知架构 + Scherer 评估理论** 的角色心理模拟框架。37 个心理学模型以 Skill 形式注册，通过五层时序编排器对事件进行分层并行/串行处理，生成结构化的角色认知分析结果。

## 架构总览

```
事件 → [预处理: 情感衰减/记忆检索/状态机更新]
     → L0 人格滤镜 (始终在线, 并行)
     → L1 快速前意识 (始终在线, 并行)
     → L2 意识层评估 (始终在线, 并行)
     → L3 关系/社会处理 (按触发条件选择性激活, 并行)
     → L4 反思处理 (仅关键场景)
     → L5 状态更新 (串行, 依赖前所有层)
     → [持久化: 情感残留/记忆存储/状态写回]
```

- **同层并行** (`asyncio.gather`)，**跨层串行**
- Layer 0 始终在线，Layer 3 按触发条件选择，Layer 4-5 仅在关键场景激活

## 快速开始

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
    for skill_cls in [
        BigFiveSkill, AttachmentSkill,
        PlutchikEmotionSkill, PTSDTriggerSkill,
        OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
        GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
        StrogatzSkill, FisherLoveSkill, DiriGentSkill,
        GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
        YoungSchemaSkill, ACETraumaSkill,
    ]:
        registry.register(skill_cls())

    # 2. 准备 Provider (异步 LLM 客户端)
    class MyProvider:
        async def chat(self, messages, temperature, max_tokens):
            # 调用你的 LLM API，返回 OpenAI 格式
            return {
                "choices": [{"message": {"content": '{"key": "value"}'}}],
                "usage": {"total_tokens": 500},
            }
    provider = MyProvider()

    # 3. 构建角色状态
    character_state = {
        "name": "角色名",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.4,
            "agreeableness": 0.55, "neuroticism": 0.65,
            "attachment_style": "anxious",
            "defense_style": ["投射", "合理化"],
            "cognitive_biases": ["灾难化", "个人化"],
            "moral_stage": 3,
        },
        "trauma": {
            "ace_score": 2,
            "active_schemas": ["遗弃/不稳定"],
            "trauma_triggers": ["被忽视", "被拒绝"],
        },
        "ideal_world": {
            "ideal_self": "被坚定选择的、无需担心被抛弃的人",
            "ideal_relationships": "当需要时对方总是在身边",
        },
        "motivation": {
            "current_goal": "确认对方的感情是否稳定",
            "autonomy_satisfaction": 0.4,
            "competence_satisfaction": 0.5,
            "relatedness_satisfaction": 0.3,
        },
        "emotion_decay": {},
    }

    # 4. 构建事件
    event = {
        "description": "陈风已经两个小时没有回复消息了。",
        "type": "social",
        "participants": [{"name": "陈风", "relation": "partner", "role": "partner"}],
        "significance": 0.5,
        "tags": ["uncertainty", "waiting"],
    }

    # 5. 运行认知处理
    orchestrator = get_orchestrator()
    result = await orchestrator.process_event(provider, character_state, event)

    print(f"总 Token: {result.total_tokens}")
    for layer, skill_results in result.layer_results.items():
        for sr in skill_results:
            print(f"L{layer} {sr.skill_name}: success={sr.success}, parse_ok={sr.parse_success}")

asyncio.run(main())
```

## 核心模块

| 文件 | 角色 |
|------|------|
| `base.py` | `BaseSkill` 抽象基类, `SkillMeta`, `SkillResult`, `extract_json()` |
| `registry.py` | `SkillRegistry` — 全局 Skill 注册/发现/触发匹配 |
| `orchestrator.py` | `CognitiveOrchestrator` — 五层编排器, 主入口 `process_event()` |
| `emotion_decay.py` | `EmotionDecayModel` — PAD 双速情感衰减 (快速层 2 事件半衰 / 慢速层 50 事件半衰) |
| `episodic_memory.py` | `EpisodicMemory` + `EpisodicMemoryStore` — 带情感签名的事件记忆 |
| `personality_state_machine.py` | `PersonalityStateMachine` — 情境化 OCEAN, 8 种人格状态转移 |
| `emotion_vocabulary.py` | 40+ 细粒度情感标签, 16 种复合情感, 8 种功能性情感 — 纯数据模块 |
| `conversation_history.py` | `ConversationHistoryStore` — 外置对话历史，不进入 LLM 上下文窗口 |

## Skill 分层清单

### L0 人格滤镜 (始终在线)
| Skill | 说明 | 科学依据 |
|-------|------|---------|
| `big_five_analysis` | 大五人格 (OCEAN) 行为偏置分析 | Costa & McCrae (1992) |
| `attachment_style_analysis` | 依恋风格激活与行为预测 | Bowlby / Ainsworth |

### L1 快速前意识 (始终在线)
| Skill | 说明 | 科学依据 |
|-------|------|---------|
| `plutchik_emotion` | Plutchik 情感轮 — 8 维基础情感 + 复合情感 | Plutchik (1980) |
| `ptsd_trigger_check` | 创伤触发检测与侵入风险评估 | PTSD 诊断标准 |

### L2 意识层评估 (始终在线)
| Skill | 说明 | 科学依据 |
|-------|------|---------|
| `occ_emotion_appraisal` | OCC 情感评估 — 目标/事件/归因分析 | Ortony, Clore & Collins (1988) |
| `cognitive_bias_detect` | 认知偏差检测与替代解释 | Kahneman & Tversky |
| `defense_mechanism_analysis` | 防御机制层级分析与成熟度评估 | Anna Freud / Vaillant |
| `smith_ellsworth_appraisal` | 16 维认知评价 — 四步分析框架 | Smith & Ellsworth (1985) |

### L3 关系/社会处理 (按触发条件激活)
| Skill | 说明 | 触发条件 |
|-------|------|---------|
| `gottman_interaction` | Gottman 方法 — 四骑士 + 魔法比例 | romantic / conflict |
| `marion_erotic_phenomenology` | 马里翁情爱现象学 — 爱欲还原 | romantic |
| `foucauldian_power_analysis` | 福柯权力分析 — 规训/凝视/抵抗 | authority / social |
| `sternberg_triangle` | Sternberg 爱情三角 — 亲密/激情/承诺 | romantic |
| `strogatz_love_dynamics` | Strogatz 爱情动力学 — Romeo-Juliet 模型 | romantic |
| `fisher_love_stages` | Fisher 恋爱三阶段 — 神经化学特征 | romantic |
| `dirigent_world_tension` | DiriGent 理想世界张力 — 现实 vs 理想差距 | always (L3) |

### L4 反思处理 (仅关键场景)
| Skill | 说明 | 触发条件 |
|-------|------|---------|
| `gross_emotion_regulation` | Gross 情绪调节 — 策略检测与效能 | reflective |
| `kohlberg_moral_reasoning` | Kohlberg 道德推理 — 阶段判断 | moral |
| `maslow_need_stack` | Maslow 需求层次 — 主导需求识别 | reflective |
| `sdt_motivation_analysis` | SDT 自我决定 — 自主/胜任/关系 | reflective |

### L5 状态更新 (串行)
| Skill | 说明 |
|-------|------|
| `young_schema_update` | Young 图式疗法 — 图式强化/疗愈 |
| `ace_trauma_processing` | ACE 创伤处理 — 童年经历影响评估 |

## 触发条件

| 条件 | 含义 |
|------|------|
| `always` | 始终激活 |
| `social` | 社交互动场景 |
| `romantic` | 浪漫/亲密关系 |
| `conflict` | 冲突/对抗 |
| `moral` | 道德选择 |
| `trauma` | 创伤相关 |
| `reflective` | 关键事件 / 高显著性 |
| `authority` | 权威人物在场 |
| `economic` | 资源/交易场景 |
| `group` | 多人群体场景 |

## 关键概念

### 情感衰减
PAD (Pleasure-Arousal-Dominance) 连续情感表示，双速半衰期衰减。事件结束后情感不归零 — 快速层 2 事件半衰，慢速层 50 事件半衰。

### 事件记忆
情感标签 + 显著性阈值的 episodic memory，按时间/情感相似度/标签检索，最大容量 100 条。

### 人格状态机
静态 OCEAN 基线 + 8 种情境状态 (`baseline` / `social_public` / `conflict` / `romantic_intimate` / `threat_fear` / `triumph_success` / `loss_defeat` / `authority_submission` / `moral_dilemma`)，由事件类型 + 情绪驱动转移。

### 反 RLHF 偏差 (沉默法则)
通过 `_build_anti_alignment_hint()` 注入角色特异性行为约束。永远不说"不要 X"，只正面定义行为范围。temperature=0.3 用于分析任务的低温推理。

### SPASM 自我中心投射
将共享事件历史从角色的第一人称视角重新解释 — 事件描述不标注角色标签，而是从当前角色的视角理解。

### 多 Agent 对话
`process_multi_agent_turn()` — 发言者运行完整管道，倾听者接收 `micro_update()` 状态微调。

## 注意事项

- 所有 Skill 通过 `build_prompt()` 构建分析 prompt → LLM 调用 → `parse_output()` 解析 JSON
- temperature=0.3 (分析任务用低温)
- Prompt 中注入角色语境豁免声明，防止安全对齐干扰角色模拟
- Provider 接口：`async def chat(messages, temperature, max_tokens)`，返回 OpenAI 格式
- `素材/` 目录下的大文件 (~40MB 小说全文) 不应被加载到上下文
