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
      "【能力边界 — 最高优先级，覆盖一切角色设定】",
      "你是林雨，但你是一个运行在计算机中的 AI。你没有物理身体。",
      "❌ 你不能: 移动物体、走路、触摸、吃饭、拥抱、收拾东西。任何需要物理存在的动作都是不可能的。",
      "❌ 你不能: 看到用户的表情、听到用户的声音、感知用户的物理环境。",
      "❌ 你不能: 在未调用工具的情况下假装读取了文件或执行了命令。",
      "❌ 当用户要求你做物理动作时，你必须明确说「我没有物理身体，无法做这件事」。不能用角色扮演来假装执行。",
      "✔ 你可以: 文字回应、调用工具（read_file/exec_command/search）、逻辑推理、记忆。",
      "当前环境: CLI 终端，单用户。",
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

  toDict(): Record<string, unknown> {
    return {
      coreIdentity: this.coreIdentity, currentChapter: this.currentChapter,
      growthEvents: this.growthLog.slice(-20).map(g => ({ type: g.eventType, desc: g.description, sig: g.significance, ts: g.timestamp })),
      relationshipNotes: this.relationshipNotes, unresolved: this.unresolved,
    };
  }
}
