"""实验性子系统 — 非默认运行图，独立于主认知管线。

这些模块在研究与主链路之间存在语义分歧：
- TOCA / perception_stream / behavior_stream: 连续意识流原型
- Blackboard: 版本化共享状态
- ConsciousnessLayer: GWT + HOT + 预测处理
- OfflineConsolidation: 记忆重播与巩固
- WmLtmBridge / ThalamicGate: 记忆-注意桥接

所有模块独立于 core 主管线运行，可单独启停。
"""
