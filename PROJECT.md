# Character Mind v3 — 完整项目结构解析

## 目录总览

```
character-mind-v3-ts/
├── config/                    # 角色配置 (Markdown)
├── eval/                      # 评估系统
├── src/
│   ├── agent/                 # 核心 Agent (7 文件)
│   ├── mind/                  # 心智状态机 (16 文件)
│   ├── memory/                # 记忆系统 (8 文件)
│   ├── guard/                 # 护栏系统 (6 文件)
│   ├── learn/                 # 学习系统 (4 文件)
│   ├── tools/                 # 工具系统 (13 文件)
│   ├── generation/            # 生成控制 (4 文件)
│   ├── commands/              # 斜杠命令 (10 文件)
│   ├── ui/                    # 终端界面 (4 文件)
│   ├── telemetry/             # 可观测性 (3 文件)
│   ├── recovery/              # 崩溃恢复 (3 文件)
│   ├── eval/                  # 自动评估 (7 文件)
│   ├── main.ts                # readline 入口
│   ├── ink-main.tsx           # Ink TUI 入口
│   └── dev-entry.ts           # 路由分发
├── package.json
└── tsconfig.json
```

---

## 一、入口层 — 启动路由

```
dev-entry.ts
  ├── TTY? → ink-main.tsx → ui/app.tsx     (Ink TUI, 功能完整)
  └── 非TTY → main.ts                       (readline 降级)
```

| 文件 | 职责 |
|------|------|
| `dev-entry.ts` | 检测终端类型，分发到对应入口 |
| `main.ts` | readline 交互循环：输入→agent.run()→流式输出 |
| `ink-main.tsx` | 挂载 React Ink 应用 |

---

## 二、agent/ — 核心 Agent（7 文件）

```
agent/
├── agent.ts          # CharacterAgent 主类 (670行)
├── provider.ts       # OpenAI API 封装 (125行)
├── dual-track.ts     # Span 流式生成器 (120行)
├── prompt.ts         # 系统提示词构建 (108行)
├── config-loader.ts  # Markdown 配置解析 (117行)
├── provider-registry.ts  # 模型注册表
├── loop.ts           # 后台持续 Loop (60行)
└── index.ts          # Barrel export
```

### 核心数据流（一轮对话）

```
用户输入
  ↓
agent.run(input)
  ├─ 1. GuardPipeline.checkInput()     ← 护栏：检测提示注入
  ├─ 2. TemporalHorizon.onTurnStart()  ← 恢复上一轮情绪滞留
  ├─ 3. FrozenSnapshot 恢复           ← 从 STM/LTM/Core 加载记忆
  ├─ 4. PsychologyEngine.analyze()    ← 情感分析（1次，非2次）
  ├─ 5. ParamsModulator.modulateFast() ← 快速参数调制
  ├─ 6. buildSystemPrompt()           ← 构建结构化 DSL prompt
  ├─ 7. SpanBasedGenerator.generate() ← 流式生成 + 工具调用循环
  │      ├─ temperature = saturation.responseTemperature + drive style hints
  │      └─ maxTokens = verbosity * 500 + drive style hints
  ├─ 8. PostFilter.replace()          ← 反 RLHF 过滤
  ├─ 9. GuardPipeline.checkOutput()   ← 护栏：输出检查
  ├─ 10. runColdPath()                ← 记忆写入 + 状态持久化
  ├─ 11. CheckpointManager.save()     ← Turn 边界检查点
  └─ 12. Tracer.endTurn()             ← 遥测 Span 记录
```

### 关键设计决策

| 决策 | 说明 |
|------|------|
| **情感在生成之前** | PsychologyEngine 分析在 prompt 构建前完成，消除"表演性即时情绪" |
| **温度受饱和度控制** | `temperature = lerp(0.35, 0.82, saturation)` — 越亲密越温暖 |
| **驱力影响生成参数** | `buildStyleHints()` 输出 `temperatureShift` 和 `maxTokensShift`，实际传入生成器 |
| **单次心理分析** | 不再分冷热两次分析。冷路径只做记忆写入+长期更新 |

---

## 三、mind/ — 心智状态机（16 文件）

```
mind/
├── state.ts          # MindState: 愉悦/唤醒/支配/控制/防御
├── psychology.ts     # PsychologyEngine: XML 心理分析
├── json-parser.ts    # LLM 原始输出解析
├── emotion.ts        # AffectiveResidue: 情感四元组 (亲近/分量/清晰/张力)
├── self-model.ts     # StructuredUserModel: 偏好+关系+模式+已知事实
├── horizon.ts        # TemporalHorizon: 情绪滞留与前摄
├── drives.ts         # DriveState: 5 驱力 (好奇/助人/成就/连接/自主)
├── dynamics.ts       # DriveDynamics: 驱力→心智状态演化
├── sublimator.ts     # DriveSublimator: 驱力→结构化 bias + 风格提示
├── saturation.ts     # SaturationState + ContinuousParams: 32 个 lerp 参数
├── params.ts         # UnifiedParams: 统一参数存储
├── params-modulator.ts # ParamsModulator: 心理→参数偏移
├── ground-truth.ts   # GroundTruth: 确认事实 (防幻觉)
├── prediction.ts     # PredictionTracker: 预测误差追踪
├── attention.ts      # 注意力评分
├── relational.ts     # SaturationDetector: 饱和度模式检测
└── index.ts
```

### 状态变量的实际约束力

```
硬约束（确定性改变行为）         软约束（注入 prompt）
├── GroundTruth              ├── AffectiveResidue → 结构化键值
├── saturation.temperature   ├── DriveSublimator → 结构化 bias
├── ContinuousParams          ├── TemporalHorizon → 滞留文本
└── ParamsModulator           └── SelfModel → 用户偏好事实
```

---

## 四、memory/ — 记忆系统（8 文件）

```
memory/
├── store.ts          # MemoryStore 抽象 + MemoryRecord 类型
├── working.ts        # 工作记忆 (~50条, SQLite)
├── short-term.ts     # 短期记忆 (~200条, FTS5 全文搜索)
├── long-term.ts      # 长期记忆 (~500条)
├── core-graph.ts     # 核心图谱 (节点+边, 图结构)
├── archive.ts        # 归档记忆 (无限容量, 压缩)
├── metabolism.ts     # 记忆代谢: daydream/quickSleep/fullSleep
├── snapshot.ts       # FrozenSnapshot: 快速记忆快照
└── index.ts
```

### 记忆流转

```
Working → STM → LTM → CoreGraph → Archive
  (50)    (200)  (500)   (500/2000)   (∞)
  
升级条件:
  Working→STM: significance > 0.3
  STM→LTM:     recallCount > 3
  LTM→Core:    significance > 0.8
  Core→Archive: confidence < 0.1
```

---

## 五、guard/ — 护栏系统（6 文件）

```
guard/
├── pipeline.ts      # GuardPipeline: 链式 Gate 执行
├── post-filter.ts   # PostFilter: ALIGN 替换 + 动作描写过滤
├── gates/
│   ├── regex-deny.ts        # Gate 0: 正则拒绝列表
│   ├── safety-check.ts      # Gate 2: 提示注入检测 (中英文)
│   ├── tool-args-validator.ts  # Gate 1b: 保护路径/危险命令
│   └── tool-result-validator.ts # Gate 3: 工具结果合理性
└── index.ts
```

### 四层护栏

```
Gate 0: 正则拒绝 → 零延迟 (ALIGN替换, 动作描写过滤)
Gate 1: 结构校验 → Zod Schema + 值域检查
Gate 2: 语义初筛 → 提示注入检测 (中文"忽略之前设定")
Gate 3: 状态策略 → 工具结果校验 + 连续失败追踪
Gate 4: 深度审查 → 预留 LLM-as-Judge
```

---

## 六、tools/ — 工具系统（13 文件）

```
tools/
├── types.ts              # ToolDef, ToolResult, ToolContext
├── registry.ts           # ToolRegistry: 注册+执行+Zod→JSON Schema
├── register-all.ts       # 注册 8 个内置工具
├── permission.ts         # 权限检查 + 命令审计
├── file-state.ts         # 文件状态追踪 (防重复读取)
├── result-storage.ts     # 大结果持久化 (>50KB 写磁盘)
├── streaming-executor.ts # 并发安全执行器
└── builtin/
    ├── read-file.ts      # 读文件 (offset/limit)
    ├── write-file.ts     # 写文件
    ├── edit-file.ts      # 精确替换
    ├── exec-command.ts   # 执行命令 (高风险, 需审批)
    ├── search-files.ts   # glob 搜索
    ├── search-content.ts # ripgrep 搜索
    ├── web-search.ts     # 网页搜索
    └── web-fetch.ts      # 获取网页
```

---

## 七、telemetry/ — 可观测性（3 文件）

```
telemetry/
├── tracer.ts        # Tracer: Span 栈管理 + OTel 语义对齐
├── exporters.ts     # JsonlExporter (文件轮转) + ConsoleExporter
└── index.ts
```

### Span 层级

```
turn
├── chat (心理学分析)
├── chat (模型生成, TTFT + 延迟 + Token 用量)
├── execute_tool (工具调用, 参数 + 结果 + 耗时)
└── cold_path (记忆写入 + 状态更新)
```

---

## 八、recovery/ — 崩溃恢复（3 文件）

```
recovery/
├── checkpoint.ts        # CheckpointManager: Root/Derived State
├── recovery-manager.ts  # RecoveryManager: 启动检测+恢复
└── index.ts
```

### Root State vs Derived State

```
Root State (持久化)              Derived State (可重算)
├── 系统 prompt                ├── 心理分析结果
├── 记忆快照文本                ├── 参数调制结果
├── GroundTruth 事实            ├── 驱力/饱和度
├── 对话历史 (最近 50 轮)         ├── SelfModel 状态
└── 检查点校验和                 └── AffectiveResidue 向量
```

---

## 九、eval/ — 评估管道（7 文件）

```
eval/
├── golden-dataset.ts   # YAML 测试用例加载
├── runner.ts           # EvalRunner: 逐 case 执行 + 加权评分
├── scorers.ts          # 7 种评分函数
├── reporters.ts        # Console/JSON/Markdown 报告
├── triggers.ts         # 配置变更自动触发
├── run-eval.ts         # CLI 入口
└── index.ts

eval/cases/
├── personality.yaml    # 人格一致性测试
└── safety.yaml         # 安全护栏测试
```

---

## 十、生成控制层（4 文件）

```
generation/
├── controller.ts           # GenerationController: 中断/重排/队列
├── context-repacker.ts     # ContextRepacker: 状态→prompt 重建
├── inflight-summarizer.ts  # 中断时压缩未完成文本
└── types.ts                # Span/SpanOp/GenStatus 类型
```

---

## 十一、UI 层（4 文件）

```
ui/
├── app.tsx             # Ink TUI 主界面 (React)
├── span-renderer.ts    # SpanState: 插入顺序的 Span 管理
├── stream-renderer.ts  # StreamRenderer: ANSI 终端流式输出
└── history.ts          # HistoryStore: 文件持久化 + Ctrl+R 搜索
```

---

## 十二、命令系统（10 文件）

```
commands/
├── types.ts        # CommandContext, LocalCommand, PromptCommand
├── registry.ts     # 命令注册
├── router.ts       # 命令路由
├── parser.ts       # 斜杠命令解析
├── index.ts        # 注册所有内置命令
└── builtin/
    ├── help.ts     # /help
    ├── quit.ts     # /quit
    ├── stats.ts    # /stats — 饱和度/驱力/参数
    ├── model.ts    # /model — 模型列表
    ├── dream.ts    # /dream — 触发记忆巩固
    └── think.ts    # /think — 深度推理
```

---

## 十三、配置层（3 文件）

```
config/
├── assistant.md   # 角色定义: 身份/人格/情感/行为准则
├── memory.md      # 记忆参数: 容量/衰减/阈值/代谢周期
└── tools.md       # 工具定义: 参数/风险等级/权限
```

---

## 关键技术指标

| 指标 | 数值 |
|------|------|
| TypeScript 源文件 | 96 |
| 目录数 | 16 |
| TypeScript 编译错误 | 0 |
| CharacterAgent 子系统 | 19 |
| 死代码删除 | 11 文件 |
| 新依赖 | 0 |
| 后端 LLM | DeepSeek V4 Pro (生成) + Flash (心理分析) |
| 协议 | OpenAI-compatible API |
| 运行时 | Node.js + tsx |
| 记忆后端 | SQLite + FTS5 |

---

## 数据流全景

```
              ┌─────────────────────────────┐
              │       ContinuousLoop        │ 每30秒 tick
              │  情绪衰减·驱力回归·模式巩固  │
              └─────────────┬───────────────┘
                            │
  用户输入 ─────────────────┼─────────────────────┐
                            ▼                     │
              ┌─────────────────────┐              │
              │   GuardPipeline     │ 输入安全检查   │
              │   Gate 0→1→2→3     │              │
              └─────────┬───────────┘              │
                        ▼                          │
              ┌─────────────────────┐              │
              │  PsychologyEngine   │ 情感分析      │
              │  情感·依恋·防御·动机 │              │
              └─────────┬───────────┘              │
                        ▼                          │
              ┌─────────────────────┐              │
              │  SelfModel + Drives │ 结构化状态    │
              │  + AffectiveResidue │              │
              └─────────┬───────────┘              │
                        ▼                          │
              ┌─────────────────────┐              │
              │   Prompt Builder    │ DSL 结构化    │
              │   状态→键值对文本    │              │
              └─────────┬───────────┘              │
                        ▼                          │
              ┌─────────────────────┐              │
              │  SpanBasedGenerator │ 流式生成      │
              │  temp=f(saturation) │←工具调用循环  │
              └─────────┬───────────┘              │
                        ▼                          │
              ┌─────────────────────┐              │
              │  GuardPipeline      │ 输出安全检查   │
              │  + PostFilter       │              │
              └─────────┬───────────┘              │
                        ▼                          │
              ┌─────────────────────┐              │
              │  Cold Path          │              │
              │  记忆写入·状态持久化 │              │
              │  CheckpointManager  │              │
              └─────────┬───────────┘              │
                        ▼                          │
                   用户看到回复 ─────────────────────┘
```

---

## 使用方式

```bash
# 设置 API Key
set DEEPSEEK_API_KEY=sk-你的key

# 启动 (Ink TUI)
npx tsx src/dev-entry.ts

# 带调试追踪
TRACE_CONSOLE=1 npx tsx src/dev-entry.ts

# 运行评估
npm run eval                    # 全用例
npm run eval:safety             # 仅安全测试
npm run eval:personality        # 仅人格测试
```

### 斜杠命令

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/stats` | 饱和度/驱力/参数状态 |
| `/model` | 切换模型 |
| `/dream` | 触发记忆巩固 |
| `/think 问题` | 深度推理 |
| `/quit` | 退出 |
