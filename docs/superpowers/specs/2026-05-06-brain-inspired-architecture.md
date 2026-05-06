# Brain-Inspired Architecture: Online/Offline Dual-State TOCA

## 核心架构：在线-离线双状态

```
在线模式（外部输入活跃）
  感知 → 丘脑门控(过滤) → 选择性管道 → 回应
                                ↓
                          显著事件 → 存入记忆

离线模式（无输入5s+）
  Nudge Engine 触发 → 轻量实例(L0+L4) → 重播记忆
       → 巩固到 Blackboard → 图式更新/反思
       → 工作记忆 ←→ 长期记忆交互
```

## 四个组件

### 1. 丘脑门控 (Thalamic Gate)
- 每个感知进入前快速评分：情绪强度、新颖性、目标相关性
- 低于阈值 → 累积在 Blackboard 缓冲区
- 累积效应超过阈值 → 触发完整管道
- 零额外 Token（纯数学评分）

### 2. 离线巩固 (Offline Consolidation)
- 借鉴 Hermes Nudge Engine: N 次显著事件后触发
- Fork 轻量实例：只跑 L0+L4，不跑 L5（不生成回应）
- 重播近期高显著性记忆
- 更新 Blackboard: 图式强化/疗愈, ACE 轨迹, 人格微调
- 完全后台，不影响主会话

### 3. 工作记忆 ↔ 长期记忆 (WM ↔ LTM)
- 感知窗口运行时检测与历史记忆的情感相似度
- 匹配成功 → 从 EpisodicMemoryStore 检索 → 注入工作记忆
- 角色"想起过去"→ 影响当前分析

### 4. 层次化预测 (Hierarchical Prediction)
- L1: 预测下一帧情绪状态 (PAD)
- L2: 预测认知评估变化 (goal_conduciveness, certainty)
- L4: 预测反思触发 (是否需要深度处理)
- 各层独立计算预测误差 → 误差驱动显著性

## 实现文件

- `core/thalamic_gate.py` — 感知过滤
- `core/offline_consolidation.py` — Nudge Engine + 后台重播
- `core/wm_ltm_bridge.py` — 工作记忆-长期记忆桥接
- 扩展 `core/consciousness.py` — 层次化预测
- 扩展 `core/toca_runner.py` — 双状态调度

## 验证
- `python tests/validation/toca_single_test.py` 无回归
- 离线模式触发验证: 输入停止后5s自动进入
- 丘脑门控验证: 低显著性感知被过滤
