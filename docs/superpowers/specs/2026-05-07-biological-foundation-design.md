# Biological Foundation Layer — 让角色模拟更像真人

## 1. 问题与目标

现有5层认知管道 (L0-L5) 是纯反应式的——事件来了→处理→回应。缺少：
- **内部驱力**：角色没有"想要"、没有饥饿/疲劳/社交需求驱动的主动行为
- **生物时间动态**：情绪有衰减但没有神经化学基础，无法解释"为什么有些情绪更持久"
- **预测处理**：consciousness.py 有简单预测但无精度加权、无主动推理
- **人格-生物桥接**：OCEAN与依恋风格没有转化为可计算的生物参数

生物基础层解决"角色为什么主动做某事"的问题，而非仅"角色如何回应事件"。

## 2. 总体架构

```
事件 → [L-3 驱力系统] → [L-2 HPA轴] → [L-2 递质引擎] → [L-1 主动推理桥接]
                                                              ↓
     → [L0 人格] → [L1 情绪] → [L2 评价] → [L3 社交] → [L4 反思] → [L5 回应]
                                                              ↓
     [L-1 预测误差反馈] ← [L-2 递质更新] ← [L-3 驱力满足]
```

### 数据流

1. L-3 驱力随时间和事件衰减/满足，产生"需求张力"
2. L-2 HPA轴响应压力事件，CORT缓慢升降，调制所有递质增益
3. L-2 递质引擎基于OCEAN基线和事件响应，更新DA/5-HT/NE/OXT水平
4. L-1 主动推理层将驱力→先验偏好，递质→精度参数，计算预期自由能驱动行动倾向
5. L0-L5 认知管道接收生物参数注入（mood_bias、精度权重、行动倾向）
6. 认知处理结果反馈 → 递质更新 → 驱力满足 → HPA调节

## 3. L-3: 稳态驱力系统

### 3.1 驱力层次（Tyrrell 1993 + Panksepp 1998）

**生存核心层（3个）：**
1. 能量/饥饿 (energy) — 随时间衰减，进食事件满足
2. 安全/威胁 (safety) — 事件驱动，安全确认满足
3. 休息/睡眠 (rest) — 随时间衰减，休息事件满足

**哺乳动物层（4个）：**
4. 社交归属 (social) — 随时间衰减，社交互动满足
5. 新奇/探索 (novelty) — Panksepp SEEKING系统，随时间衰减，新信息满足
6. 能力/掌控 (competence) — 失败受挫，成功满足
7. 自主/控制 (autonomy) — 被控制时衰减，自由选择满足

**丰富层（5个）：**
8. 温度/舒适 (comfort) — 环境不适时衰减
9. 繁殖/浪漫 (mating) — 随时间缓慢衰减，亲密满足
10. 养育/关怀 (care) — Panksepp CARE系统
11. 地位/权力 (status) — 被尊重时满足，被轻视时衰减
12. 公平/正义 (justice) — 不公事件衰减

**元驱力（3个）：**
13. 探索/寻找 (SEEKING) — Panksepp基础探索驱力，独立于其他驱力
14. 玩耍/快乐 (PLAY) — Panksepp PLAY系统
15. 恐惧/恐慌 (PANIC) — Panksepp PANIC系统，分离痛苦

### 3.2 核心计算

每个驱力 `i` 的状态更新：

```
h_i(t+1) = h_i(t) + decay_i * dt                      # 自然衰减
           - consumption_i(action_t) * dt               # 行动消耗/满足
           + event_impact_i(event_t, significance)      # 事件冲击
           - h_i(t) * regulation_i * dt                 # 自我调节
           
h_i ∈ [0, h_max],  低于 0.2 = 满足,  高于 0.8 = 临界
```

驱力强度（动机张力）：

```
drive_i(t) = (h_i - h*_i)^2 / (h*_i)^2    # 二次型，接近临界时急剧上升
```

### 3.3 行动选择（Tyrrell自由流层次结构）

驱力之间通过 **W-Learning** (Humphrys 1995) 竞争：每个驱力维护自己的Q函数，当前"如果不被选中将损失最多"的驱力获得控制权。

```
W_i = max_a Q_i(s, a) - Q_i(s, a_chosen)   # 驱力i如果不被选中会损失多少
selected_drive = argmax_i W_i * drive_i(t)  # 损失最大且最紧急的驱力获胜
```

正常情况下使用分布式投票（软性过渡），临界驱力 > 0.8 时切换为赢家通吃（危机模式）。

## 4. L-2b: HPA轴 (完整ODE)

### 4.1 状态变量

基于 Sriram et al. (2012) 的5变量模型：

```
CRH (促肾上腺皮质激素释放激素)     — 下丘脑释放
ACTH (促肾上腺皮质激素)           — 垂体释放
CORT (皮质醇)                     — 肾上腺释放
GR (糖皮质激素受体二聚体)          — 介导负反馈
GR_total (总受体)                  — 受表观遗传调控
```

### 4.2 ODE 系统

```
d[CRH]/dt = k_basal                                          # 基础分泌
           + k_stress * stress_input(t)                      # 压力输入
           - V_crh * [CRH] / (K_crh + [CRH])                # 降解
           - k_fb * [GR]^2 * [CRH] / (K_fb + [CRH])        # GR负反馈

d[ACTH]/dt = k_acth * [CRH]                                 # CRH刺激
            - V_acth * [ACTH] / (K_acth + [ACTH])           # 降解
            - k_fb * [GR]^2 * [ACTH] / (K_fb + [ACTH])     # GR负反馈

d[CORT]/dt = k_cort * [ACTH]                                # ACTH刺激
            - V_cort * [CORT] / (K_cort + [CORT])           # 降解

d[GR]/dt = k_syn * [GR_total]                              # 受体合成
          - k_deg * [GR]                                     # 降解
          - 2 * k_on * [CORT] * [GR]^2                     # CORT结合
          + 2 * k_off * [GR_dimer]                          # 解离
```

### 4.3 关键参数

| 参数 | 正常值 | PTSD | 抑郁 |
|------|--------|------|------|
| k_stress (压力敏感性) | 1.0 | 2.5 | 1.5 |
| k_fb (负反馈强度) | 1.0 | 0.4 | 1.8 |
| K_fb (反馈EC50) | 0.5 | 1.2 | 0.3 |
| GR_total (总受体) | 1.0 | 0.6 | 0.8 |

ACE分数 → GR_total降低 (NR3C1甲基化) → 负反馈减弱 → CORT基线升高/峰值钝化。

### 4.4 时间常数

- CRH半衰期: ~8 min
- ACTH半衰期: ~15 min
- CORT半衰期: ~90 min
- GR适应: ~hours-days

## 5. L-2a: 神经递质引擎

### 5.1 5递质系统

每个递质有：**基线**(由OCEAN/Ace/依恋决定) + **相位响应**(事件驱动) + **紧张响应**(驱力调制) + **衰减**(回归基线) + **受体适应**(慢速)。

```
NT(t+1) = NT(t) + (NT_baseline - NT(t)) / tau_decay    # 回归基线
          + phasic_event(event)                          # 事件相位响应
          + tonic_drive(drive_state)                     # 驱力紧张调制
          + noise                                         # 随机波动
```

### 5.2 递质特异性参数

| 递质 | 基线来源 | tau_decay | 加速相位响应的事件 |
|------|---------|-----------|------------------|
| DA | E×0.6 + O×0.3 | 5 min | 奖励、目标达成、新奇 |
| 5-HT | (1-N)×0.7 + C×0.2 | 30 min | 安全确认、公平对待、休息 |
| NE | N×0.5 + E×0.2 | 10 min | 威胁、新奇、任务需求 |
| CORT | ACE×0.4 + N×0.3 | 90 min | 压力事件（来自HPA轴输出） |
| OXT | A×0.5 + 依恋 | 15 min | 社交接触、信任行为、抚摸 |

### 5.3 受体适应（慢速）

```
d(receptor_sensitivity)/dt = (1.0 - sensitivity) / tau_up
                            - NT_level * sensitivity / tau_down

tau_up ~ days (上调)
tau_down ~ hours-days (下调/脱敏)
```

受体适应产生：
- **耐受**：长期高NT → 受体下调 → 需要更多NT才能达到相同效果
- **敏感化**：长期低NT → 受体上调 → 少量NT即可产生大效果
- **戒断**：NT突然降低 + 受体已下调 → 强烈负反应

### 5.4 递质间相互作用

```
DA_eff = DA_raw * (1 - w_5ht_da * 5HT)     # 5-HT抑制DA效果
5HT_eff = 5HT_raw * (1 - w_cort_5ht * CORT) # CORT抑制5-HT效果
NE_eff = NE_raw * (1 + w_cort_ne * CORT)    # CORT增强NE效果
OXT_eff = OXT_raw * (1 - w_ne_oxt * NE)     # NE抑制OXT效果
```

## 6. L-1: 主动推理桥接层

### 6.1 核心功能

不替换现有L0-L5管道。作为生物层(L-3, L-2)与认知层(L0-L5)之间的计算桥接：

1. 将驱力状态 → 先验偏好 (C矩阵)
2. 将递质水平 → 精度参数 (π)
3. 计算预期自由能 → 行动倾向
4. 计算预测误差 → 情绪强度修正

### 6.2 生成模型组件

```
A矩阵 (似然): P(observation | hidden_state)
  — 不需要完全学习，使用驱力→情绪的已知映射

B矩阵 (转移): P(hidden_state_{t+1} | hidden_state_t, action)
  — 编码"如果我采取行动X，驱力Y会如何变化"
  — 可以预置部分知识（如"进食减少饥饿"），然后通过经验学习

C向量 (偏好): P(observation) ∝ exp(-drive_deviation)
  — preferred_obs = argmin_{obs} sum_i drive_i(obs)
  — 角色偏好驱力满足的状态

D向量 (初始信念): P(initial_state)
  — 当前驱力状态作为先验
```

### 6.3 信念更新（感知推理）

```
# 当前观察 = 驱力状态
obs = [h_energy, h_safety, h_social, h_novelty, ...]

# 预测: 给定当前信念和可能的行动，预期观察是什么
predicted_obs(pi) = A · B(pi) · current_belief

# 预测误差 (精度加权)
prediction_error(pi) = precision_weight · (obs - predicted_obs(pi))

# 精度权重由递质决定
precision_weight = {
    "reward": DA_eff,
    "threat": NE_eff,
    "social": OXT_eff,
    "interoceptive": 1.0 / (1.0 + exp(-5 * (NE_eff - 0.5))),
}

# 更新后验信念
belief(t+1) = softmax(log(belief(t)) + sum_pi precision_weight_pi * prediction_error_pi)
```

### 6.4 预期自由能与行动倾向

```
G(pi) = -E_{Q(o|pi)}[ln P(o|C)]           # 工具价值：预期结果与偏好的匹配度
        + D_KL[Q(s|pi) || P(s|o,pi)]       # 认知价值：减少多少不确定性

# 工具价值 = 预期驱力减少
instrumental_value = drive_state(t) - expected_drive_state(t+1 | pi)

# 认知价值 = 信息增益（好奇心）
epistemic_value = entropy(belief(t)) - expected_entropy(belief(t+1) | pi)

# 综合
G(pi) = -instrumental_value - exploration_weight * epistemic_value

# 行动倾向
action_tendency = softmax(-G / temperature)
# temperature 由 NE 调制: temperature = base_temp * (1 + NE_eff)
```

### 6.5 预测误差 → 情绪修正

```
# 预测误差映射到情绪维度
prediction_surprise = ||obs - predicted_obs||          → Plutchik surprise
reward_prediction_error = actual_reward - expected_reward → DA相位响应(+ = 喜悦, - = 失望)
threat_prediction_error = actual_threat - expected_threat → NE相位响应(+ = 恐惧)

# 精度调节情绪强度
emotional_intensity_correction = precision_weight * prediction_error
```

### 6.6 与现有管道的集成

主动推理层的输出注入现有管道的上下文：

```python
ctx["biological_context"] = {
    "drives": drive_state,                    # 15驱力当前值
    "dominant_drive": winning_drive,          # 当前最紧急的驱力
    "action_tendency": action_tendency,       # 预期自由能导出的行动倾向
    "prediction_surprise": prediction_error,  # 预测误差(情绪修正)
    "neurotransmitters": {
        "DA": DA_level, "5HT": 5HT_level,
        "NE": NE_level, "CORT": CORT_level, "OXT": OXT_level,
    },
    "precision_weights": precision_weights,   # 各通道的精度权重
    "hpa_state": {"CRH": CRH, "ACTH": ACTH, "CORT": CORT, "GR": GR},
}
```

现有技能通过 `context["biological_context"]` 访问这些参数，用于：
- L0 人格: 递质水平影响行为偏置的强度
- L1 情绪: 预测误差修正 Plutchik emotion 强度
- L2 评价: 精度权重影响 OCC 评价的确定性
- L3 社交: OXT水平影响 TheoryOfMind 的信任先验
- L4 反思: CORT水平影响 GrossRegulation 的策略选择
- L5 回应: 行动倾向影响 response_generator 的 action 选择

## 7. 实现文件结构

```
core/
  biological/           # 新增生物基础模块
    __init__.py
    drive_system.py      # L-3: 15驱力 + W-Learning + 行动选择
    hpa_axis.py          # L-2b: CRH→ACTH→CORT→GR ODE
    neurotransmitter.py  # L-2a: 5递质 + 受体适应 + 相互作用
    active_inference.py  # L-1: 生成模型 + 精度加权 + 预期自由能
    biological_state.py  # 统一状态容器 + 序列化
    biological_bridge.py # 与现有管道的集成适配器

skills/
  # 无需修改 — 通过 biological_context 注入

core/
  orchestrator.py        # 修改: process_event 前增加生物层更新
  consciousness.py       # 修改: 精度参数从生物层获取
  emotion_decay.py       # 修改: 半衰期由CORT调节
  personality_state_machine.py  # 可选: OCEAN→NT基线映射
  thalamic_gate.py       # 修改: 门控阈值由NE调节
```

## 8. 实现优先级

Phase A: 核心生物状态 + 递质引擎 + 驱力系统 (L-2, L-3)
Phase B: HPA轴ODE (L-2b)
Phase C: 主动推理桥接 (L-1)
Phase D: 受体适应 + 跨递质相互作用
Phase E: 与L0-L5管道的完整集成

## 9. 验证方式

1. 单元测试: 驱力衰减/满足的正确性，递质回归基线的时间常数
2. 集成测试: 高CORT→情绪衰减半衰期延长→负面情绪更持久
3. 角色一致性: 高E角色DA基线更高→更频繁的趋近行为
4. 压力动态: 连续压力事件→HPA轴漂移→CORT升高→行为变化
5. LLM-as-Judge: 对比有/无生物层的角色回应质量
