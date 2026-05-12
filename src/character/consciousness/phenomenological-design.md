# 现象学动力架构 — 完整设计

## 原则

不从"系统设计"出发，从"体验的结构"出发。每个设计对应一个现象学概念。

---

## 四层架构

```
══════════════════════════════════════════════
层 0: 被动情感层（被动综合 + 情感调谐 + 内隐记忆）
══════════════════════════════════════════════
  现象学对应: 胡塞尔被动综合 + 海德格尔 Befindlichkeit
  Agent 对应: AffectiveResidue（新模块）
  
  不是"检索到的记忆"
  而是"过去互动被动沉积成的情感底色"
  不进入显意识，但给一切上色

  存储: 每次互动 → 提取情感签名 → 累积到沉积向量
  注入: 不是文本，是模糊感受 — "你感到一种熟悉的温暖底色"
  遗忘: fading — 旧沉积权重随时间衰减

══════════════════════════════════════════════
层 1: 时间意识域（滞留 + 原印象 + 前摄）
══════════════════════════════════════════════
  现象学对应: 胡塞尔内时间意识三相位
  Agent 对应: TemporalHorizon（新模块）
  
  不是"状态快照存档/加载"
  而是"仍在回响的上一个当下" + "已经期待的即将到来"

  滞留: 上轮的情感残差，衰减但仍在影响
  前摄: 对下一轮的预期张力，落空时触发不安/好奇
  自主tick: 不是计时器→主动说话，而是前摄张力超过阈值

══════════════════════════════════════════════
层 2: 主动评估层（情调-揭示 + 评估反馈）
══════════════════════════════════════════════
  现象学对应: 梅洛-庞蒂身体-主体 + 萨特反思
  Agent 对应: 改造 PsychologyEngine 输入层

  不是"客观输入 + 反应分析"
  而是"输入在情调中被揭示为特定意义"
  同一输入在不同情调下是不同的现象

  层 0 输出 → 情调底色 → 输入被揭示 → 层 2 分析

══════════════════════════════════════════════
层 3: 叙事自我层（反思 + 闭环叙事）
══════════════════════════════════════════════
  现象学对应: 丹尼特叙事自我 + 萨特反思悖论
  Agent 对应: SelfModel + 闭环（改造现有模块）

  不是"记录参数变化"
  而是"对自己的体验的持续叙述"
  Cold Path 心理观察 → SelfModel 续写 narrative
  Hot Path 只读 narrative text，不读 raw params

══════════════════════════════════════════════
```

---

## 新模块设计

### 模块 1: AffectiveResidue（被动情感沉积层）

**现象学基础**: 胡塞尔"被动综合"——相似的经验自动联想，形成前反思的感受底色。

```
位置: src/character/consciousness/affective-residue.ts

class AffectiveResidue:
  // 情感沉积向量 — 不存储事件，只存储感受的累积
  residue: {
    warmth: number       // 亲近感 (-1..1)
    weight: number       // 关系的分量感 / 重要性 (0..1)
    clarity: number      // 对这个人/话题的清晰度 (0..1)
    tension: number      // 未解的张力 (0..1)
  }

  // 每次 Cold Path 后更新
  deposit(eventEmotion: EmotionResult, significance: number):
    // 高 significance → 沉积更深
    // 情感强度 → 决定沉积哪个维度
    // 不是简单叠加，是共振——和已有沉积的相似度决定影响大小
    // 旧沉积自然衰减 (半衰期可配置)

  // Hot Path 注入
  formatForPrompt():
    不输出数值
    把沉积向量转换为 1 句中文描述
    
    warmth > 0.5 → "你感到一种熟悉的亲近"
    warmth < -0.3 → "你隐约有些距离感"
    tension > 0.4 → "你感到还有话没说出口"
    clarity < 0.3 → "你觉得这个人还不太清晰"
    
    如果各维度都在中性区间 → 返回空字符串（不说废话）

  // 遗忘: 不是删除，是 fading
  tick(dt: number):
    所有沉积值向 0 衰减
    衰减速度 = 半衰期参数
```

### 模块 2: TemporalHorizon（时间视域）

**现象学基础**: 胡塞尔"滞留-原印象-前摄"结构。当下不是点，是域。

```
位置: src/character/consciousness/temporal-horizon.ts

class TemporalHorizon:
  // 滞留残差 — 上轮完成后留下的情感回响
  retention: {
    emotion: Record<string, number>   // 上轮结束时的主要情感
    intensity: number                  // 残留强度 (随时间衰减)
    unfinished: boolean                // 上轮是否感觉没说完
    sinceLastTurn: number              // 距上轮多少秒
  }

  // 前摄张力 — 预期中的下一轮
  protention: {
    expectingResponse: boolean         // 是否预期用户会说话
    expectedTopic: string              // 预期的话题方向
    tension: number                    // 张力 (等待越久张力越高)
    tensionThreshold: number           // 超过此值可能触发主动行为
  }

  // 轮次边界回调
  onTurnStart():
    保留上轮的 retention
    重置 protention 张力
  
  onTurnEnd(turnResult):
    从本轮的 psych 结果计算 retention 残差
    设置 protention — "接下来会聊什么"

  // 自主 tick (在 Controller 里轮询)
  tick(dt: number):
    retention.intensity *= decay(dt)
    protention.tension += growth(dt)
    
    if protention.tension > threshold:
      触发主动转向
      (未来功能: agent 主动说 "我一直在想...")

  formatForPrompt():
    retention 强 → "刚才的感受还在"
    protention 张力高 → (未来: 触发主动行为)
    大部分时候返回空 — 这不是每轮都要说的东西
```

### 模块 3: 驱力升华注入器

**现象学基础**: 弗洛伊德升华 + 梅洛-庞蒂"我能先于我想"。

驱力值永不被注入 prompt。只通过两个通道影响行为。

```
位置: src/character/drive/sublimator.ts

class DriveSublimator:
  // 输入: 驱力向量 (来自 DriveState)
  // 输出: 自然语言描述 (用于 prompt) + 采样参数偏移

  // 通道 A: 注意力偏向
  buildAttentionBias(drives: DriveState): string
    不是 "curiosity=0.8"
    而是翻译为自然语言感受:
    
    high curiosity → "你发现自己对这个话题有很深的兴趣"
    high connection → "你想靠近对方，了解ta更多"
    high autonomy → "你感到自己今天很独立，不太需要别人的认可"
    
    BUT: 只在驱力显著偏离基线时才注入
    大部分时候不输出——避免每句都"你感到..."
  
  // 通道 B: 语调偏移
  buildStyleModulation(drives: DriveState): StyleHints
    low autonomy → 更多试探用词, 更短, temperature 微降
    high achievement → 更精确, 更完整, repetition_penalty 微调
    high connection → 更多用对方名字, 更长的回应
    
    返回的不是文本，是采样参数的建议偏移:
    { temperatureShift: +0.05, maxTokensShift: +50 }

  // 驱力之间的竞争: 只让最强的驱力表达
  selectDominantDrives(drives: DriveState, topN = 2):
    多个驱力同时高 → 只选最强 1-2 个表达
    其他保持沉默——避免 prompt 拥挤
```

### 模块 4: 状态循环 — SelfModel 闭环

**现象学基础**: 丹尼特叙事自我 + 萨特反思悖论。
Cold Path 的自我观察 → 续写自我叙事 → Hot Path 只读叙事文本。

```
改造现有: src/character/consciousness/self-model.ts

新增方法:
  updateNarrative(psychologyResult):
    从 psych 提取 2-3 个关键变化
    翻译成 1 句自然语言，更新 current_chapter
    
    规则:
      情感有显著变化 → "我发现自己今天比平时更___"
      关系有变化 → "和他在一起时，我感到___"
      防御激活 → "刚才我好像有些___"
      有未解问题 → "我还在想___"
    
    不更新所有维度——只在有显著变化时更新
    保持 current_chapter 的简洁（1-2 句）

  formatForHotPath():
    返回 current_chapter
    不暴露任何参数值
    如果 current_chapter 是旧的 (超过 N 轮没更新) → 微调措辞

改造: character-agent.ts 的 runColdPath()

  当前:
    Cold Path 做 psych 分析 → 更新参数 → 结束
    
  闭环:
    Cold Path 做 psych 分析 
      → 更新参数 (Fast/Slow modulation)
      → 更新 AffectiveResidue (deposit)
      → 更新 SelfModel (updateNarrative)
      → 下次 Hot Path 读 formatForHotPath()
      → 形成叙事闭环
```

### 模块 5: 评估反馈 — 情调-揭示机制

**现象学基础**: 事件在情调中**被揭示**。同一输入在不同底色下是不同的现象。

```
改造现有: src/character/mind/psychology-engine.ts

当前:
  analyze(event, memoryContext, mindState) → psych result
  输入被当作"客观事件"分析

改造:
  analyze(event, memoryContext, mindState, affectiveContext)
  新增参数: affectiveContext (来自 AffectiveResidue)
  
  在 prompt 中改变事件描述的框架:
    不是: "用户对你说了 ___"
    而是: 
      高 warmth: "[在亲近的氛围中] 用户对你说了 ___"
      高 tension: "[你们之间有些微妙的张力] 用户对你说了 ___"
      低 clarity: "[你还不太确定这个人] 用户对你说了 ___"

  这个框架词不是"指令"——它改变 LLM 感知事件的方式
  LLM 自然会在分析中体现不同的感知方向
```

---

## 数据流总览

```
用户输入
  ↓
[TemporalHorizon] 前摄张力归零，滞留进入
  ↓
[AffectiveResidue] 被动情感底色 → 模糊感受描述
  ↓
[DriveSublimator]
  ├─ 注意力偏向 → 模糊感受描述 (偶尔)
  └─ 语调偏移 → style hints
  ↓
[情调-揭示] 输入在情感底色中被重新框架
  ↓
[PsychologyEngine] 评估 (接受重新框架后的输入)
  ↓
[Prompt Builder] 组装 prompt
  ├─ 层 0: AffectiveResidue 感受 (模糊)
  ├─ 层 1: TemporalHorizon retention (如显著)
  ├─ 层 2: DriveSublimator 注意力偏向 (如显著)
  ├─ 层 3: SelfModel narrative (当前自我状态)
  ├─ 层 4: 任务/命令/规则
  └─ 层 5: 记忆快照 (高意义事件)
  ↓
[SpanBasedGenerator] 生成
  ├─ Style hints → temperature 微调
  └─ Fast + Slow Track
  ↓
[Cold Path]
  ├─ PsychologyEngine.analyze (完整分析)
  ├─ AffectiveResidue.deposit (被动沉积)
  ├─ SelfModel.updateNarrative (叙事更新)
  ├─ DriveState.applyReward (驱力更新)
  └─ TemporalHorizon.onTurnEnd (设置滞留+前摄)
  ↓
(闭环) → 下次 Hot Path 从更新的各层读取
```

---

## 实施顺序

### Phase A: AffectiveResidue (最有收益)
新建 1 个文件: `affective-residue.ts`
最小改动: Cold Path 里加一行 `deposit()`, Prompt Builder 里加一层注入

### Phase B: DriveSublimator + SelfModel 闭环
改造 `self-model.ts` 加 `updateNarrative()`
新建 `drive/sublimator.ts`
改造 Prompt Builder 使用新的注入来源

### Phase C: TemporalHorizon
新建 `temporal-horizon.ts`
改动 Controller 加 tick 轮询

### Phase D: 情调-揭示
改造 PsychologyEngine._buildPrompt() 接受 affective context
最小改动——只是给事件描述加一个框架词
