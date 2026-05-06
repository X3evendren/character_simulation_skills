# TOCA: Temporal Overlay Cognitive Architecture

## 时间叠加认知架构 — 连续状态流设计

### 问题

当前架构是离散事件批处理：事件→五层分析→回应。每次处理完状态被"冻结"，下次事件再"解冻"。真实心理活动没有回合边界——状态永远在流动。

### 核心思想

**不是 11 个不同的 Agent。是同一个五层管道，在时间偏移上运行多个实例。**

```
单次管道耗时 T ≈ 3s（DeepSeek Flash）
实例数 N = 3
间隔 = T/N = 1s

t=0: [实例1: L0──L1──L2──L3──L4──L5] ──────────────────→ 写入Blackboard(t=3)
t=1:      [实例2: L0──L1──L2──L3──L4──L5] ──────────────────→ 写入(t=4)
t=2:           [实例3: L0──L1──L2──L3──L4──L5] ──────────────────→ 写入(t=5)
t=3: 完成←[1]  [实例4: L0──L1──L2──L3──L4──L5] ──────────────→ 写入(t=6)
t=4: 完成←[2]       [实例5: L0──L1──L2──L3──L4──L5] ──────────→ 写入(t=7)
...

每秒都有新的心理状态更新写入 Blackboard
```

**连续性从何而来**：
- 每个实例启动时读取 Blackboard 上的**最新状态**（可能是上一个实例刚写入的）
- 实例之间形成因果接力：实例2看到实例1的情绪变化，实例3看到实例2的防御激活...
- 间隔 = 推理时间/N，体感无缝

---

## 一、架构组件

### 1. 感知流 (Perception Stream)
```
连续输入，不是完整事件:
[
  {t:0.0, modality:"visual", content:"手机屏幕亮了"},
  {t:0.2, modality:"visual", content:"不是他的消息"},
  {t:1.0, modality:"internal", content:"他在忙吗？"},
  {t:3.0, modality:"visual", content:"朋友圈看到他在线"},
  {t:3.1, modality:"somatic", content:"胸口发紧"},
  ...
]
```

每个管道实例读取自己时间窗内的感知片段。实例4（t=3启动）的窗口是 [t=0, t=3]。

### 2. 管道实例 (Pipeline Instance)

```
与当前 process_event() 完全相同:
  _prepare_context() → L0 → L1 → L2 → L3 → L4 → L5 → response
  读取: Blackboard最新状态 + 自己时间窗内的感知流
  写入: Blackboard（状态更新） + BehaviorStream（行为输出）
```

**关键差异**：不再等"事件结束"。每个实例在启动时"截取"当前 Blackboard 快照 + 感知流窗口，处理后写回。

### 3. Blackboard (共享状态)
```python
Blackboard = {
    # L0
    "active_ocean": {"O":0.6, "C":0.5, "E":0.4, "A":0.55, "N":0.65},
    "personality_state": "baseline",
    
    # L1 — 高频变化
    "pad": {"pleasure": -0.2, "arousal": 0.5, "dominance": -0.1},
    "dominant_emotion": "fear",
    "emotion_intensity": 0.55,
    "threat_level": 0.3,
    "ptsd_triggered": False,
    
    # L2
    "active_appraisal": {...},
    "active_biases": [{"name":"灾难化", "intensity":0.6}],
    "active_defense": {"name":"情感隔离", "level":3},
    
    # L3
    "social_context": {...},
    "tom_inferences": {...},
    
    # L4
    "moral_stance": {...},
    
    # L5
    "pending_response": {"text":"...", "confidence":0.8},
    "schema_changes": [...],
    
    # 元数据
    "_last_update": 1712345678.123,
    "_updating_instance": 4,
}
```

每个字段带 `_version` 计数器，实例写入时自增。实例读取时记录版本号，写入时检查是否有冲突（乐观锁）。

### 4. 行为流 (Behavior Stream)
```
连续输出:
[
  {t:0.5, type:"micro_expression", content:"皱眉"},
  {t:1.2, type:"action", content:"拿起手机又放下"},
  {t:3.5, type:"somatic", content:"深呼吸"},
  {t:6.0, type:"internal_monologue", content:"别想太多"},
  {t:9.0, type:"speech", content:"你在忙吗？"},
  {t:9.5, type:"micro_expression", content:"咬嘴唇"},
]
```

ResponseGenerator 在管道末尾检查 confidence。高于阈值 → 产生行为输出。低于阈值 → 跳过（内心活动继续，但不外显）。

---

## 二、状态连续性机制

### 实例间因果接力

```
实例1 (t=0-3):
  读取: 基线状态 + [t=-3, t=0]感知
  发现: 手机没消息 → PAD.pleasure 从0→-0.1
  写入: pad = {p:-0.1, a:0.3, d:0.0}

实例2 (t=1-4):
  读取: 更新后的 pad + [t=-2, t=1]感知 (新增: "不是他的消息")
  发现: 继续等待 → PAD.pleasure从-0.1→-0.3, fear上升
  写入: pad = {p:-0.3, a:0.5, d:-0.1}, dominant_emotion=fear

实例3 (t=2-5):
  读取: 进一步恶化的状态 + [t=-1, t=2]感知 (新增: "朋友圈看到在线")
  发现: 被忽视确认 → PAD剧变, threat_level=0.7, 灾难化偏差激活
  写入: pad={p:-0.6, a:0.8, d:-0.4}, threat=0.7, active_biases=[灾难化]

实例4 (t=3-6):
  读取: 危机状态 + 前面积累的所有感知
  发现: 防御机制启动 → 情感隔离
  写入: active_defense={情感隔离}, ResponseGenerator输出"你在忙吗？"
```

每个实例"站在前人的肩膀上"。没有跳跃，没有冻结。

---

## 三、记忆系统

三层，从快到慢：

```
感知流 ──→ Working Memory (60s滑动窗口, 高精度)
              │
              ▼ 显著性>0.3 或 情感变化>0.5
           Episodic Buffer (最近N个片段, 情感标记)
              │
              ▼ 反思时 (L4 Reflection触发)
           Long-Term Memory (图式/关系/人格, 结构化)
```

- **Working Memory**：管道实例直接读取。60秒内所有感知 + 情感状态变化。自动淘汰旧数据。
- **Episodic Buffer**：当某个实例检测到显著性变化时，当前 WM 快照被捕获。不是自动存所有，而是"值得记住的时刻"。
- **Long-Term Memory**：现有 EpisodicMemoryStore，但不再是"事件归档"，而是状态流的河床——约束流向但不冻结。

---

## 四、Token 消耗

```
单次管道 ≈ 15,000 tokens (22个Skill × 平均700 tokens)
N = 3 实例, 间隔 1s

每分钟: 60次管道运行 × 15K tokens = 900K tokens/min
DeepSeek价格: ~¥2/百万token
每分钟成本: ~¥1.8
每小时成本: ~¥108
```

**优化策略**：

| 策略 | 效果 |
|------|------|
| 本地小模型跑 L0-L2 | 降低 60% API Token |
| 管道缓存 (同 prompt 前缀) | 降低 30% prompt Token |
| 降低 N 到 2 | 间隔 1.5s，成本减半 |
| Delta 跳过 (状态变化<阈值时跳过完整管道) | 降低 40-60% 运行次数 |

---

## 五、与当前架构的关系

```
当前 process_event() = TOCA 的"单实例模式"
  - 输入: 完整事件
  - 运行: 一次完整管道
  - 输出: 单次回应
  - 用途: 关键场景深度分析、benchmark 测试、离线批处理

TOCA 连续模式
  - 输入: 感知流
  - 运行: N 个管道实例时间偏移交叉
  - 输出: 连续行为流
  - 用途: 实时对话、游戏 NPC、AI 伴侣
```

同一套 Skill、同一个编排器。只是运行调度方式不同。

---

## 六、实现路线

### Phase 1: 核心引擎
- `core/blackboard.py` — 版本化共享状态 + 乐观锁
- `core/toca_runner.py` — 时间偏移实例调度器
- `core/perception_stream.py` — 连续感知流 + 时间窗切片

### Phase 2: 适配
- 扩展 `orchestrator.py` 支持从 Blackboard 读取 / 不依赖完整事件
- ResponseGenerator 增加 confidence 门控

### Phase 3: 优化
- Delta 跳过逻辑
- 管道前缀缓存

### Phase 4: 验证
- 2角色连续对话场景
- 与批处理模式行为一致性对比
- Token 基准
