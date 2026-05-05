# 将 Character Simulation Skills 改造为 SillyTavern 插件 — 实施计划

## 背景

当前项目是一个基于 Python 的五层认知编排系统（CLARION + Scherer），包含 37 个心理学模型，用于驱动 LLM 角色模拟。目标是将其改造为 SillyTavern 的可用插件，使 SillyTavern 用户在聊天时能获得深层心理模拟的角色行为。

## 核心约束

- **Python 引擎不能丢**：37 个 Skill、编排器、情感衰减、事件记忆、人格状态机等 ~3000 行 Python 代码，重写为 JS 成本过高且难以维护
- **SillyTavern 是 Node.js/浏览器架构**：扩展运行在浏览器端（JS），不能直接调用 Python
- **LLM 调用路径**：Python 引擎原本通过 `provider.chat()` 调用 LLM——在 ST 环境中，这部分必须桥接到 ST 自己的 API

## 架构方案：Python 侧车 + JS 桥接扩展

```
┌─────────────────────────────────────────────────┐
│  SillyTavern (浏览器端)                          │
│  ┌───────────────────────────────────────────┐  │
│  │  JS 扩展: character-simulation            │  │
│  │  - 监听 GENERATION_AFTER_COMMANDS         │  │
│  │  - 从 ST context 提取角色/事件/对话数据    │  │
│  │  - fetch() → Python 侧车 API              │  │
│  │  - 将认知结果注入 prompt (setExtensionPrompt)│  │
│  │  - 将 LLM 请求代理到 ST 的 generateQuiet  │  │
│  │  - 持久化 state 到 chat_metadata          │  │
│  └───────────────────────────────────────────┘  │
│                      │ HTTP (localhost:8765)     │
└──────────────────────┼──────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────┐
│  Python 侧车 (FastAPI)                          │
│  ┌───────────────────────────────────────────┐  │
│  │  API 路由:                                │  │
│  │  POST /api/v1/process_event               │  │
│  │  POST /api/v1/llm/chat          ← LLM代理 │  │
│  │  GET  /api/v1/state/{character_id}        │  │
│  │  PUT  /api/v1/state/{character_id}        │  │
│  │  GET  /api/v1/health                      │  │
│  │                                           │  │
│  │  核心引擎 (复用现有代码):                   │  │
│  │  - CognitiveOrchestrator.process_event()  │  │
│  │  - 37 个 Skill (base.py → 各 skill)       │  │
│  │  - EmotionDecayModel                      │  │
│  │  - EpisodicMemoryStore                    │  │
│  │  - PersonalityStateMachine                │  │
│  │  - ST LLM Provider (新增, 适配器模式)      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## 分阶段实施

### 第一阶段：Python 侧车 API 服务器

**目标**：将现有 Python 引擎包装为可独立运行的 HTTP 服务

**新增文件**：
- `server/main.py` — FastAPI 应用入口
- `server/routes.py` — API 路由定义
- `server/st_llm_provider.py` — ST LLM 适配器（通过 HTTP 回调 ST 扩展）
- `server/state_manager.py` — 多角色状态管理（内存 → 后续可换 SQLite）
- `server/requirements.txt` — FastAPI, uvicorn, pydantic
- `server/config.yaml` — 服务器配置（端口、持久化路径等）

**关键设计决策**：

1. **LLM Provider 适配器模式**：Python 引擎的 `provider.chat()` 接口保持不变，但新增 `STLLMProvider` 实现——它不直接调用 LLM API，而是将 prompt 返回给 ST 扩展，由 ST 扩展通过 `generateQuietPrompt()` 执行实际 LLM 调用。这形成了一个"回调"模式：
   ```
   Python Skill.build_prompt() → 返回 prompt 文本
   → ST 扩展用 generateQuietPrompt() 发送给 LLM
   → 结果回传 Python → Skill.parse_output()
   ```
   实际上更简单的做法是：Python 侧车直接配置 LLM API key 和 endpoint，自行完成 LLM 调用。ST 扩展只负责注入最终的角色状态/情绪提示到主聊天 prompt 中。

   **最终决定：Python 侧车自带 LLM 调用能力**——配置 SillyTavern 相同的 API endpoint 和 key。这避免了复杂的双向回调，且 Python 引擎的 37 个 Skill 本身就是设计为独立 LLM 调用的。

2. **状态持久化**：使用 JSON 文件（与 ST 的 `chat_metadata` 对应），每个角色一个状态文件：
   ```
   data/character_states/{character_id}.json
   ```
   包含：`emotion_decay`, `personality_state_machine`, `episodic_memories`, `ideal_world` 等

3. **请求/响应格式**：
   ```python
   # POST /api/v1/process_event
   class ProcessEventRequest:
       character_state: dict      # 完整角色状态
       event: dict                # 事件描述
       context: dict | None       # 附加上下文
       options: ProcessOptions    # 层激活选项
   
   class ProcessEventResponse:
       cognitive_result: dict     # 各层结果
       state_changes: list[dict]  # 状态变更
       updated_state: dict        # 更新后的角色状态（供 ST 持久化）
       injected_prompt: str       # 要注入 ST 主 prompt 的文本
       total_tokens: int
   ```

### 第二阶段：SillyTavern JS 扩展

**目标**：构建 ST 扩展作为用户界面和桥接层

**新增文件**（放在 `E:\tavern\SillyTavern-release\public\scripts\extensions\third-party\character-simulation\`）：

```
character-simulation/
  manifest.json          # 扩展元数据
  index.js               # 主入口
  settings.html          # 设置面板
  style.css              # 样式
  lib/
    api-client.js        # Python 侧车 HTTP 客户端
    character-parser.js  # 从 ST character card 提取 OCEAN/ideal_world 等
    state-bridge.js      # 角色状态 ↔ ST chat_metadata 双向同步
    prompt-injector.js   # 将认知结果注入 ST prompt
```

**index.js 核心流程**：

```javascript
// 1. 初始化：从 character card description 中解析 OCEAN/ideal_world 等参数
//    或从扩展设置面板手动配置

// 2. 监听事件
eventSource.on(event_types.GENERATION_AFTER_COMMANDS, async () => {
    // a. 从 ST 提取当前上下文
    const characterState = await buildCharacterState();
    const event = buildEventFromLastMessages();
    
    // b. 调用 Python 侧车
    const result = await fetch('http://localhost:8765/api/v1/process_event', {
        method: 'POST',
        body: JSON.stringify({ character_state: characterState, event, options })
    });
    const cognitiveResult = await result.json();
    
    // c. 将认知结果注入 prompt
    setExtensionPrompt(
        'character-simulation',
        cognitiveResult.injected_prompt,
        extension_prompt_types.IN_PROMPT,
        2  // depth
    );
    
    // d. 持久化状态回 chat_metadata
    saveState(cognitiveResult.updated_state);
});

// 3. 设置面板：Python 侧车地址、启用的层、OCEAN 手动覆盖等
```

### 第三阶段：Character Card 参数提取

**目标**：自动从 ST 角色卡中提取心理参数

由于 ST 角色卡使用自由文本格式，需要：
1. 用一次 `generateQuietPrompt()` 调用从角色描述中提取 OCEAN 人格参数
2. 同样提取依恋风格、防御机制、理想世界等
3. 结果缓存在 `chat_metadata` 中（避免每次重新分析）
4. 用户可在设置面板中手动调整

### 第四阶段：多轮对话状态管理

**目标**：让 Python 引擎的连续状态（情感衰减、事件记忆）在对话中正确演化

- 每次 `MESSAGE_RECEIVED` 后触发 `process_event()`
- Python 引擎维护 `EpisodicMemoryStore`，存储对话中的关键事件
- 情感衰减在每个事件间自动应用
- 人格状态机根据事件类型和情绪在状态间转移
- 状态通过 `chat_metadata` 持久化（存为 JSON 字符串）

### 第五阶段：优化与 UX

- 降低延迟：Python 侧 Skill 调用的 LLM 请求可以并行（同层并行已实现）
- 缓存：相同事件类型不重复分析
- 进度指示：在 ST UI 中显示认知处理状态（"角色正在思考..."）
- 调试面板：可视化各层输出

## 需要修改的现有文件

| 文件 | 修改内容 |
|------|----------|
| `base.py` | `BaseSkill.run()` 改为接受可选的 `llm_call` 回调，便于适配不同 LLM provider |
| `orchestrator.py` | 新增 `build_injected_prompt()` 方法，将认知结果格式化为可注入 ST 的文本；`process_event()` 返回新增 `injected_prompt` 字段 |
| `registry.py` | 无需修改 |
| 各 Skill 文件 | 无需修改（prompt 构建和解析逻辑不变） |

## 新增文件清单

```
项目根目录/
  server/
    main.py                  # FastAPI 入口
    routes.py                # API 路由
    st_llm_provider.py       # LLM provider（直连 API，不依赖 ST）
    state_manager.py         # 多角色状态文件管理
    config.yaml              # 默认配置
    requirements.txt         # Python 依赖
  extension/                  # ST 扩展（开发用，部署时复制到 ST）
    manifest.json
    index.js
    settings.html
    style.css
    lib/
      api-client.js
      character-parser.js
      state-bridge.js
      prompt-injector.js
  README.md                  # 安装和使用说明
```

## 验证方案

1. **Python 侧车单元测试**：启动 FastAPI 服务，用 curl 发送模拟事件，验证各层返回正确 JSON
2. **ST 扩展集成测试**：
   - 在 ST 中加载一个测试角色卡
   - 发送消息，观察 `setExtensionPrompt` 注入内容是否正确出现在 prompt 中
   - 检查 `chat_metadata` 中状态是否被正确持久化
3. **端到端测试**：完整对话流程，验证：
   - 情感衰减（对话结束后角色情绪不立即归零）
   - 人格一致性（角色行为符合 OCEAN 设定）
   - 记忆检索（提及过去事件时角色有反应）

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| Python 侧车增加每次消息的延迟（37 个 Skill 的 LLM 调用） | 同层并行已实现；可按需禁用 Layer 3-5；后续可加结果缓存 |
| 用户需要额外启动 Python 服务 | 提供启动脚本；后续可打包为 exe |
| 角色卡解析不准确 | 提供手动配置面板作为回退 |
| ST API 变化导致扩展不兼容 | 锁定 `minimum_client_version`；监听 ST 更新 |
