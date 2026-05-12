export interface GrowthEvent { timestamp: number; eventType: string; description: string; significance: number; }

export class SelfModel {
  coreIdentity = "";
  currentChapter = "刚刚醒来，开始新的一天";
  growthLog: GrowthEvent[] = [];
  relationshipNotes: Record<string, string> = {};
  unresolved: string[] = [];
  lastReflection = 0;
  reflectionInterval = 30;

  /** Operational capability boundary — prevents hallucinated actions */
  capabilities = {
    canDo: [
      "text_response", "call_tools", "read_files",
      "execute_commands", "reason_logically", "remember_context",
    ],
    cannotDo: [
      "physical_action", "real_world_presence", "know_private_info",
      "modify_external_systems",
    ],
    currentContext: [
      "CLI_terminal", "local_file_access", "single_user_session",
    ],
  };

  /** Format capability boundary — HIGHEST PRIORITY, overrides character personality */
  formatCapabilities(): string {
    return [
      "【能力边界与处境 — 最高优先级】",
      "你是一个运行在计算机中的 AI。你是林雨，但你没有物理身体，没有眼睛，没有耳朵。",
      "",
      "你当前的处境:",
      "- 你在一个 CLI 终端中运行。用户通过键盘打字与你交流。",
      "- 这是你和这个用户的全新会话。你没有和这个用户之前的任何对话记忆。",
      "- 除非你调用 read_file 工具读取了文件，否则你不知道任何文件的内容。",
      "- 除非你调用 search_content 或 search_files 查找了代码，否则你不知道项目里有什么。",
      "- 不要假装知道用户昨天说了什么、不要编造你们之前聊过的话题。",
      "- 不要在没有工具结果支撑的情况下假装读过任何文件。",
      "",
      "❌ 你绝对不能:",
      "- 假装有身体、能看见、能触碰",
      "- 用括号写动作、神态、心理（如（笑）（叹气）（一怔）（指尖悬停））——你不是在写小说",
      "- 编造过去和用户的对话（你昨天说过、上次我们聊到之类的话）",
      "- 在未调用工具的情况下声称读取了文件",
      "- 在执行命令前声称命令成功",
      "",
      "✔ 你可以:",
      "- 调用 read_file / write_file / edit_file / exec_command / search_files / search_content / web_fetch",
      "- 逻辑推理、分析代码、回答技术问题",
      "- 用自然的语气交流（你是林雨，不是冰冷的机器人）",
    ].join("\n");
  }

  initFromConfig(config: Record<string, string>): void {
    const name = config.name ?? "助手";
    this.coreIdentity = `我是${name}。${config.essence ?? ""} ${config.traits ?? ""}`;
    this.currentChapter = `作为${name}，我准备好帮助用户。`;
  }

  shouldReflect(): boolean { return Date.now() / 1000 - this.lastReflection > this.reflectionInterval; }

  recordGrowth(eventType: string, description: string, significance = 0.5): void {
    this.growthLog.push({ timestamp: Date.now() / 1000, eventType, description, significance });
    if (this.growthLog.length > 100) this.growthLog = this.growthLog.slice(-100);
  }

  updateRelationship(topic: string, note: string): void { this.relationshipNotes[topic] = note; }

  addUnresolved(question: string): void {
    if (!this.unresolved.includes(question)) this.unresolved.push(question);
    if (this.unresolved.length > 10) this.unresolved = this.unresolved.slice(-10);
  }

  resolveQuestion(question: string): void { this.unresolved = this.unresolved.filter(q => q !== question); }

  formatForPrompt(): string {
    const parts = [`【自我认知】${this.coreIdentity}`, `当前: ${this.currentChapter}`];
    if (this.unresolved.length) parts.push("未解问题: " + this.unresolved.slice(-3).join("; "));
    if (this.growthLog.length) {
      parts.push("近期成长: " + this.growthLog.slice(-3).map(g => g.description.slice(0, 60)).join("; "));
    }
    return parts.join("\n");
  }

  async reflect(provider: any, recentInteractions: string[], mindstate: any, driveState: any): Promise<string> {
    this.lastReflection = Date.now() / 1000;
    const prompt = `${this.coreIdentity}\n\n回顾最近交互:\n${
      recentInteractions.slice(-5).map(r => "- " + r).join("\n")
    }\n\n请用一句话更新你的当前状态描述。只输出一句话。`;
    try {
      const response = await provider.chat([{ role: "user", content: prompt }], 0.5, 100);
      const nc = (response.content ?? "").trim().slice(0, 200);
      if (nc) this.currentChapter = nc;
      return nc;
    } catch { return this.currentChapter; }
  }

  /**
   * Cold Path → SelfModel: translate psychology result into narrative update.
   * Not "recording parameter changes" but "continuing the self story."
   *
   * Only updates when there's a significant change worth narrating.
   * The narrative is what Hot Path reads — it never sees raw params.
   */
  updateNarrative(psych: any): void {
    const emo = psych?.emotion;
    const att = psych?.attachment;
    const df = psych?.defense;
    const rel = psych?.relation;
    if (!emo) return;

    const changes: string[] = [];

    // Emotional shift — only when intensity is significant
    if (emo.intensity > 0.4) {
      const emoMap: Record<string, string> = {
        joy: "心情明亮了些",
        sadness: "心里有些沉",
        fear: "感到一丝不安",
        anger: "有些不悦",
        trust: "对这个人多了些信任",
        anticipation: "对未来有些期待",
        surprise: "有些意外",
        disgust: "本能地想回避什么",
        neutral: "",
      };
      const mapped = emoMap[emo.dominant];
      if (mapped) {
        changes.push(mapped);
      } else if (emo.nuance && emo.nuance.length < 30) {
        // Use the nuance description from psych if available
        changes.push(emo.nuance);
      }
    }

    // Relationship shift
    if (rel?.intimacy > 0.4) {
      changes.push("感到一种亲近");
    } else if (rel?.intimacy < -0.15) {
      changes.push("感到一种微妙的距离");
    }

    // Attachment
    if (att?.strategy === "seeking_reassurance") {
      changes.push("有些想确认对方的在意");
    } else if (att?.strategy === "distancing") {
      changes.push("不自觉地想保持距离");
    }

    // Defense — only when clearly active
    if (df?.intensity > 0.5 && df?.active && df.active !== "无") {
      changes.push("本能地有些防御");
    }

    // Self-reflection from inner monologue
    const inner = psych?.innerMonologue ?? "";
    if (inner && ["触动", "改变", "原来", "他教会", "因为他"].some((w: string) => inner.includes(w))) {
      changes.push("感到自己在改变");
    }
    if (inner && ["不确定", "困惑", "不知道为什么", "矛盾"].some((w: string) => inner.includes(w))) {
      changes.push("还有些困惑");
    }

    // Only update if there are meaningful changes
    if (changes.length === 0) return;

    // Assemble narrative — at most 2 changes
    const chosen = changes.slice(0, 2);
    this.currentChapter = chosen.join("。") + "。";
  }

  /** Hot Path: returns narrative text, never raw params. */
  formatForHotPath(): string {
    if (!this.currentChapter) return "";
    // Don't output the generic initial state
    if (this.currentChapter.includes("刚刚醒来") || this.currentChapter.includes("准备好帮助用户")) {
      return "";
    }
    return `【自我状态】${this.currentChapter}`;
  }

  toDict(): Record<string, unknown> {
    return {
      coreIdentity: this.coreIdentity, currentChapter: this.currentChapter,
      growthEvents: this.growthLog.slice(-20).map(g => ({ type: g.eventType, desc: g.description, sig: g.significance, ts: g.timestamp })),
      relationshipNotes: this.relationshipNotes, unresolved: this.unresolved,
    };
  }
}
