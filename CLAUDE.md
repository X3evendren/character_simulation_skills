# Character Mind v3

## 项目定位

构建一个"不真实的完美助手"——像人（有温度、有自我、有情感质感），又是完美的（强大、温柔、理解用户）。

## 架构原则

- 简单可组合：信任模型隐空间能力，用最平坦的架构 + 高质量上下文激发涌现
- 抄比写更好：参考 nanobot/Hermes/OpenClaw/ClaudeCode 的设计模式
- 纯 Markdown 配置：角色人设、工具定义、记忆参数全部用 .md 文件
- 双轨异步生成：Fast Track 抢首响应 + Slow Track 深度推理 + Merger 合成
- 统一心理引擎：一个小模型单次 XML 输出替代 24 个心理学 Skill

## 项目结构

```
config/                     Markdown 配置
  assistant.md              角色人设 + 行为规则
  tools.md                  工具定义
  memory.md                 记忆系统参数
core/
  provider.py               LLM Provider 插件式接口
  json_parser.py            LLM JSON 输出解析
  fsm.py                    对话阶段状态机
  mind_state.py             统一心理状态向量
  session.py                会话管理
  psychology/               心理推理引擎（单模型替代 24 Skill）
  drive/                    驱力+动力融合系统
  consciousness/            意识层（注意力+自我模型+预测）
  memory/                   统一记忆系统（四层分级+Sleep Cycle）
  dual_track/               双轨异步生成
  tools/                    工具系统（抄 nanobot + Hermes）
  anti_rlhf/                反RLHF 三层防护
gateway/                    HTTP + WebSocket 服务
cli.py                      命令行入口
data/                       静态数据（情感词典等）
```

## 关键概念

- **心理推理引擎**: 同一 Provider 的小模型（如 Haiku），一次调用完成全部心理学维度分析
- **五维驱力**: curiosity / helpfulness / achievement / connection / autonomy + 奖赏系统
- **四层记忆**: Working → Short-Term → Long-Term → Core 图谱 + Sleep Cycle 代谢
- **完整自我叙事**: 助手维护随经历演化的自我认知故事
- **Silence Rule**: 永远不说"不要X"——这会激活 X 的 token 权重
