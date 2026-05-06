# Consciousness Layer: 让连续状态流更接近真实意识

## 三个机制叠加

### 1. 选择性广播 (GWT) — "不是所有心理活动都进入意识"

当前：所有层的分析结果都流到 ResponseGenerator。

改为：加一个`SalienceScorer`。每个心理内容（情绪变化、威胁评估、偏差激活、防御启动...）获得一个显著性分数。只有超过阈值的才被"广播"到全局空间（即进入 L5 回应生成）。

```
L0-L4 输出 → SalienceScorer → 高显著性 → 广播 → L5 回应
                             → 低显著性 → 保留在 Blackboard（无意识加工）
```

显著性 = f(强度变化, 情感唤醒度, 目标相关性, 新颖性, 紧迫性)

### 2. 元认知自监控 (HOT) — "系统知道自己在感受什么"

新增一个周期性运行的模块。它不在五层管道内，而是在 Blackboard 层面运作：

- 读取 Blackboard 当前状态
- 生成一句话的自我评估："我正在感到焦虑，因为我解读对方的沉默为拒绝"
- 写回 Blackboard 作为 `self_perception` 字段
- 这个字段影响后续管道的显著性评分（形成自我参照循环）

### 3. 预测加工 — "惊讶驱动注意力"

每个管道实例在启动时（读 Blackboard 之后、分析之前）做一次快速预测：

- 基于当前状态预测下一帧情绪值（如：愉悦度会继续下降）
- 当实际结果出来后，计算预测误差
- 大的预测误差 → 提升该领域的显著性 → 更可能被广播 → 更可能进入意识

预测模型可以很简单（线性外推或移动平均），不需要额外的 LLM 调用。

---

## 具体改动

### 新文件

`core/consciousness.py` — 三个组件的统一实现：

```python
class ConsciousnessLayer:
    def __init__(self, blackboard):
        self.bb = blackboard
        self.prediction = {}  # 上一帧的预测
        self.salience_threshold = 0.4

    def score_salience(self, changes: dict) -> dict:
        """GWT: 计算每个心理内容的显著性分数"""
        ...

    def filter_broadcast(self, changes: dict) -> dict:
        """只返回显著度>阈值的心理内容"""
        ...

    def predict_next(self) -> dict:
        """预测加工: 基于当前状态预测下一帧"""
        ...

    def compute_prediction_error(self, actual: dict) -> dict:
        """计算预测误差，反馈到显著性"""
        ...

    def self_perceive(self) -> str:
        """HOT: 生成当前心理状态的自我描述"""
        ...
```

### 改动现有文件

`core/toca_runner.py` — `_run_instance` 中：
1. 管道开始前：调用 `predict_next()` 存储预测
2. 管道结束后：调用 `compute_prediction_error()` 更新显著性权重
3. `_write_back` 之前：调用 `filter_broadcast()` 决定哪些内容进入回应
4. 定期（每个实例或每 N 个实例）：调用 `self_perceive()` 更新自我感知

### 工作流对比

```
当前:
  感知流 → [L0-L5全量分析] → 全部写Blackboard → 回应

意识层:
  感知流 → 预测下一帧 → [L0-L5分析] → 计算预测误差
       → 显著性评分 → 筛选(>阈值才广播) → 写Blackboard
       → 自我感知更新 → 回应(仅基于广播内容)
```

---

## 验证

1. `python tests/validation/toca_single_test.py` — 行为一致性无回归
2. 手动验证：高显著性事件（威胁）比低显著性事件（日常）产生更快的回应
3. 预测误差可视化：在连续流中观察预测误差的波动

## Token 影响

- 显著性评分和预测加工：纯数学计算，零额外 Token
- 自我感知：可选调用 LLM（~300 tokens，低频），或纯模板生成（零 Token）
