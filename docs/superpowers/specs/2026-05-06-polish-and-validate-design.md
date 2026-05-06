# Polish & Validate: 系统打磨计划

## 背景

Character Simulation Skills 已完成核心架构（5层认知编排 + 22 心理学 Skill + 回应生成）。经过 Mock 验证（0.876）和 DeepSeek 真实 LLM 验证（0.882，16/4500 用例），系统在技术层面可靠但存在已知薄弱点。需要系统性打磨后对外展示。

## 目标

打磨系统至可展示状态，用 DeepSeek 完成大规模验证，建立完整的质量基线报告。

## Phase A: 已知问题修复

### A1. defense_mechanism 断言过窄
- **问题**: 预期列表只包含 2-3 种防御名，LLM 可能选择其他有效防御（如"反向形成"）
- **修复**: 在验证用例中将防御名断言从 `{"in": [...]}` 改为 `{"not_empty": true}`，仅验证产出非空
- **文件**: `tests/validation/fixtures/attachment_cases.json`, `theory_grounded_cases.json`

### A2. big_five behavioral_bias 优化
- **问题**: DeepSeek 对 Big Five 的行为偏置输出不够具体（得分 0.571）
- **修复**: 优化 `skills/l0_personality/big_five.py` 的 prompt，增加更多行为示例和 JSON 格式约束
- **验证**: 单独测试 Big Five Skill 在 DeepSeek 上的输出质量

### A3. fixture 文件清理
- **问题**: `theory_grounded_cases.json` 与 `attachment_cases.json` 等有功能重叠
- **修复**: 移除旧的 hand-crafted attachment/emotion/moral 用例，统一使用 theory_grounded 版本。保留 PersonalityEvd 和 CharacterEval 数据

## Phase B: 大规模验证

### B1. 分层抽样
- 从 4500 用例中按维度分层抽样 100 条（确保每层 >= 10 条）
- 维度: Big Five, Attachment, Emotion, Bias, Defense, Moral, Gottman, PTSD, ToM

### B2. DeepSeek 批量验证
- 运行 100 条用例，生成完整的心理学维度得分矩阵
- 记录每个 Skill 的得分、耗时、Token 消耗
- 输出验证报告

### B3. 薄弱点迭代
- 对得分 < 0.6 的 Skill 进行 prompt 优化
- 重新验证
- 最多 3 轮迭代

## Phase C: 多 Agent 首次真实测试

### C1. 构建多角色场景
- 2 角色对话: 焦虑型 vs 回避型伴侣冲突
- 3 角色对话: 权威在场 + 同伴压力
- 情感传染验证: 高神经质角色如何受对方情绪影响

### C2. DeepSeek 运行
- 验证 `process_multi_agent_turn()` 产出
- 检查 speaker_result, listener_updates, conversation_turn

## Phase D: 文档

### D1. 部署指南
- 环境变量配置 (DEEPSEEK_API_KEY 等)
- LLM 后端切换 (Ollama / DeepSeek / OpenAI)
- 基准测试和验证测试的运行方式

### D2. Skill 扩展教程
- 如何创建新 Skill
- 注册和编排
- 验证用例编写

### D3. 验证报告
- Mock vs Real LLM 对比
- 各维度得分矩阵
- 已知局限和未来方向

## 验证

每 Phase 完成后:
1. `python benchmark/run_benchmark.py --quality 0.35 --scenarios 0` 确认无回归
2. 对应 Phase 的 LLM 测试通过
3. Git commit + push
