# TOCA: Temporal Overlay Cognitive Architecture

## 时间叠加认知架构 — 连续状态流设计

### 背景

当前架构是离散事件批处理：事件→五层分析→回应。每次处理完状态被"冻结归档"，下次事件再"解冻"。这不符合真实心理活动的连续性——角色在消化上一秒感受时，下一秒刺激已进入，状态永远在流动。

### 核心思想

用多个独立 Agent 在不同时间窗口上交叉工作，共同维持一条不中断的心理状态流。没有一个 Agent 持有完整快照，状态从 Agent 之间的重叠和交互中涌现。

---

## 一、Agent 矩阵

```
时间轴 ──────────────────────────────────────────────────────→
  t=0     t=2     t=4     t=6     t=8    t=10    t=12    t=15

  [Affect Monitor ──── 2s window, every 2s ────────────────]
      [Threat Detector ──── 5s window, every 5s ──────]
          [Appraisal Engine ──── 8s window, on L1 spike ────]
                [Bias Monitor ──── 10s window, every 10s ──]
                      [Defense Monitor ──── 12s window ────]
                            [Social Context ──── 15s, triggered ────]
                                  [ToM Engine ──── 20s, on social ────]
                                        [Moral Monitor ──── 30s, low freq]
                                              [Reflection ──── 60s, rare]
  [Response Generator ──── 3s window, continuous ready ────────────────]
```

### Agent 定义

| Agent | 层级 | 时间窗 | 频率 | 触发条件 | 输入 | 输出 |
|-------|------|--------|------|---------|------|------|
| AffectMonitor | L1 | 2s | 2s | 始终 | 最近2s感知流 | PAD情感向量更新 |
| ThreatDetector | L1 | 5s | 5s | 始终 | 最近5s感知流+PAD | 威胁评分、触发状态 |
| AppraisalEngine | L2 | 8s | 按需 | PAD变化>0.3 | 最近8s+L1输出 | 认知评估 |
| BiasMonitor | L2 | 10s | 10s | 始终 | 最近10s+评估 | 活跃偏差列表 |
| DefenseMonitor | L2 | 12s | 按需 | 威胁>0.5 | 最近12s+L1+L2 | 防御机制状态 |
| SocialContext | L3 | 15s | 按需 | 检测到互动 | 最近15s+参与者 | 关系动态 |
| ToMEngine | L3 | 20s | 按需 | 社交+他人发言 | 最近20s+社交输出 | 他人心理状态推理 |
| MoralMonitor | L4 | 30s | 30s | 低频始终 | 最近30s+全部输出 | 道德评估 |
| Reflection | L4 | 60s | 按需 | 显著性>0.7 | 最近60s+全部 | 深度反思 |
| SchemaTracker | L5 | 可变 | 按需 | L1-L4共识 | 全部状态 | 图式变化 |
| ResponseGenerator | L5 | 3s | 连续 | 置信度>阈值 | 全部状态+窗口 | 微表情/行为/话语 |

---

## 二、状态共享机制

### 双层架构

```
                    ┌─────────────────┐
                    │   Event Bus     │  ← 发布/订阅消息
                    │  (轻量, 实时)    │
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │   Blackboard    │  ← 共享状态字典（版本化）
                    │  (持久, 可查询)  │
                    └─────────────────┘
```

**Event Bus**（消息总线）:
- Agent 发布变化事件：`{"type": "emotion_spike", "agent": "AffectMonitor", "delta": 0.4, "timestamp": ...}`
- Agent 订阅感兴趣的事件类型
- 轻量、实时、不持久化

**Blackboard**（黑板）:
- 所有 Agent 共享的状态字典
- 每个字段带版本号和时间戳
- Agent 可以"乐观读取"（读最新版本，不阻塞）
- 写入时检查版本冲突
- 持久化到 episodic memory

### 状态字段

```python
ContinuousState = {
    # 即时感知
    "perception_stream": deque(maxlen=60),     # 最近60s原始输入
    
    # L1: 情感（高频更新）
    "pad": {"pleasure": -0.2, "arousal": 0.5, "dominance": -0.1, "version": 15},
    "threat_level": 0.3,
    
    # L2: 认知（中频更新）
    "active_appraisal": {"goal_relevance": 0.7, ...},
    "active_biases": [{"name": "灾难化", "intensity": 0.6}],
    "active_defense": {"name": "情感隔离", "level": 3},
    
    # L3: 社交（按需更新）
    "social_context": {"participants": [...], "power_dynamic": "equal"},
    "tom_inferences": {"partner_belief": "...", "partner_intent": "..."},
    
    # L4: 反思（低频）
    "moral_stance": {"stage": 3, "conflict": "..."},
    "reflection": {"insight": "...", "triggered_at": 1712345678},
    
    # L5: 输出
    "pending_response": {"text": "...", "confidence": 0.8},
    "schema_changes": [{"schema": "遗弃", "delta": +0.1}],
    
    # 元状态
    "stream_health": {"active_agents": 8, "last_consensus": 1712345678},
}
```

---

## 三、输入/输出模型

### 输入：连续感知流

```
不是: Event { description: "伴侣两小时没回消息", type: "social" }

而是: PerceptionStream [
  {t:0.0, type:"visual", content:"手机屏幕亮了"},
  {t:0.2, type:"visual", content:"不是他的消息"},
  {t:1.0, type:"internal", content:"他在忙吗？"},
  {t:3.0, type:"visual", content:"朋友圈看到他在线"},
  {t:3.1, type:"somatic", content:"胸口发紧"},
  {t:5.0, type:"internal", content:"为什么他不回我"},
  {t:8.0, type:"auditory", content:"手机终于响了"},
  ...
]
```

### 输出：连续行为流

```
不是: "你为什么不回我消息？"（单一回应）

而是: BehaviorStream [
  {t:0.5, type:"micro_expression", content:"皱眉"},
  {t:1.2, type:"action", content:"拿起手机又放下"},
  {t:3.5, type:"somatic", content:"深呼吸"},
  {t:6.0, type:"internal_monologue", content:"别想太多"},
  {t:9.0, type:"speech", content:"（轻声）你在忙吗？"},
  {t:9.5, type:"micro_expression", content:"咬嘴唇"},
]
```

ResponseGenerator 在 3s 滑动窗口上持续运行，输出confidence>阈值时产生行为。

---

## 四、记忆系统

### 三层记忆

```
感知流 ──→ Working Memory (60s窗口, 高精度)
              │
              ▼ 显著性>0.3
           Episodic Buffer (最近N个事件片段, 情感标记)
              │
              ▼ 睡眠/反思时
           Long-Term Memory (图式/关系/人格, 结构化)
```

**Working Memory**：所有 Agent 直接读取的60秒窗口。Agent 的时间窗从 WM 中切片。

**Episodic Buffer**：当某个 Agent 检测到显著性事件时，当前 WM 快照被"捕获"存入 episodic buffer。不是自动存储所有事件，而是由 Agent 投票决定何时捕获。

**Long-Term Memory**：已有的 EpisodicMemoryStore，但在连续流中不是"事件归档"而是"状态流的河床"——它约束流向但不冻结。

---

## 五、Token 优化

### 分层策略

| 层级 | 模型 | 预估Token/次 | 频率 | 每分钟Token |
|------|------|------------|------|------------|
| L1 (Affect+Threat) | 本地 Ollama 1.5B | 200 | 30+5次 | 7,000 |
| L2 (Appraisal+Bias+Defense) | 本地 Ollama 1.5B | 400 | 6+6+5次 | 6,800 |
| L3 (Social+ToM) | DeepSeek | 600 | 按需(2-4次) | 2,400 |
| L4 (Moral+Reflection) | DeepSeek | 600 | 2+1次 | 1,800 |
| L5 (Schema+Response) | DeepSeek | 600 | 1+20次 | 12,600 |
| **总计** | | | | **~30K/分钟** |

### 优化手段

1. **Delta触发**：L2-L4 Agent 只在输入变化超过阈值时才调用LLM
2. **Prefix Cache共享**：所有 Agent 共享角色人格base prompt前缀
3. **本地模型高频层**：L1-L2用Ollama本地模型，低延迟免API费用
4. **置信度门控**：ResponseGenerator 输出前检查confidence，低置信度时跳过

---

## 六、与当前架构的关系

当前架构**保留**，作为 TOCA 的"批处理模式"子集：

```
当前 process_event() = TOCA 的"冻结帧"
  - 当需要完整深度分析时（如关键场景、转折点）
  - 当输入是完整事件而非连续流时
  - 作为 TOCA 的 baseline 和 fallback

TOCA = 连续流模式
  - 日常对话、实时交互
  - 感知流作为输入
  - Agent 时间窗口叠加
```

两者共享相同的 22 个 Skill 和 Blackboard 状态结构。

---

## 七、实现路线

### Phase 1: 基础架构（核心）
1. `core/continuous_state.py` — Blackboard + Event Bus + 版本控制
2. `core/agent_runner.py` — Agent 生命周期管理（启动/停止/时间窗调度）
3. `core/perception_stream.py` — 连续感知流输入管道
4. `core/behavior_stream.py` — 连续行为流输出管道

### Phase 2: Agent 迁移（适配现有 Skill）
5. 将现有 L0-L5 Skill 包装为 TOCA Agent（添加时间窗和触发逻辑）
6. 实现 Delta 触发逻辑

### Phase 3: 记忆系统升级
7. 三层记忆（WM → Episodic Buffer → LTM）
8. Agent 投票捕获机制

### Phase 4: 混合本地/云端
9. Ollama 本地模型集成
10. 分层模型路由

### Phase 5: 验证
11. 连续流场景测试
12. 与批处理模式对比
13. Token 消耗基准测试
