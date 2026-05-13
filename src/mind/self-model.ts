/**
 * SelfModel — Structured user model + capability boundary.
 * Replaces narrative "self-story" with structured, machine-readable state
 * that the LLM cannot ignore because it's presented as facts, not prose.
 */
export interface GrowthEvent { timestamp: number; eventType: string; description: string; significance: number; }

export interface UserPreferences {
  topics: string[];
  communicationStyle: "direct" | "indirect" | "humorous" | "unknown";
  technicalLevel: "beginner" | "intermediate" | "expert" | "unknown";
}

export interface RelationshipState {
  trust: number;       // 0-1
  familiarity: number; // 0-1
  lastInteraction: number; // timestamp
}

export interface UserPatterns {
  activeHours: number[];
  avgMessageLength: number;
  frequentRequests: string[];
}

export interface KnownFact {
  key: string;
  value: string;
  confidence: number; // 0-1
}

export class SelfModel {
  coreIdentity = "";
  growthLog: GrowthEvent[] = [];

  // Structured user model
  preferences: UserPreferences = {
    topics: [],
    communicationStyle: "unknown",
    technicalLevel: "unknown",
  };
  relationship: RelationshipState = { trust: 0.3, familiarity: 0.1, lastInteraction: 0 };
  patterns: UserPatterns = { activeHours: [], avgMessageLength: 0, frequentRequests: [] };
  knownFacts: KnownFact[] = [];

  /** Operational capability boundary */
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
  }

  // ── Interaction tracking ──

  recordGrowth(eventType: string, description: string, significance = 0.5): void {
    this.growthLog.push({ timestamp: Date.now() / 1000, eventType, description, significance });
    if (this.growthLog.length > 100) this.growthLog = this.growthLog.slice(-100);
  }

  // ── User model updates ──

  /** Record a user interaction, updating patterns and familiarity. */
  recordInteraction(input: string, _response: string): void {
    this.relationship.lastInteraction = Date.now() / 1000;
    this.relationship.familiarity = Math.min(1, this.relationship.familiarity + 0.01);

    // Update avg message length
    const len = input.length;
    if (this.patterns.avgMessageLength === 0) {
      this.patterns.avgMessageLength = len;
    } else {
      this.patterns.avgMessageLength = this.patterns.avgMessageLength * 0.9 + len * 0.1;
    }

    // Track active hour
    const hour = new Date().getHours();
    if (!this.patterns.activeHours.includes(hour)) {
      this.patterns.activeHours.push(hour);
      if (this.patterns.activeHours.length > 24) this.patterns.activeHours = this.patterns.activeHours.slice(-24);
    }
  }

  /** Update trust based on interaction outcome. */
  updateTrust(delta: number): void {
    this.relationship.trust = Math.max(0, Math.min(1, this.relationship.trust + delta));
  }

  /** Add or update a known fact about the user. */
  setFact(key: string, value: string, confidence = 0.7): void {
    const existing = this.knownFacts.find(f => f.key === key);
    if (existing) {
      existing.value = value;
      existing.confidence = Math.min(1, existing.confidence + 0.1);
    } else {
      this.knownFacts.push({ key, value, confidence });
      if (this.knownFacts.length > 50) this.knownFacts = this.knownFacts.slice(-50);
    }
  }

  /** Learn user preferences from interaction patterns. */
  learnPreference(topic: string): void {
    if (!this.preferences.topics.includes(topic)) {
      this.preferences.topics.push(topic);
      if (this.preferences.topics.length > 20) this.preferences.topics = this.preferences.topics.slice(-20);
    }
  }

  // ── Prompt formatting ──

  /** Structured user model for prompt injection — facts, not prose. */
  formatForPrompt(): string {
    const parts: string[] = [];

    // Identity
    parts.push(`【身份】${this.coreIdentity}`);

    // Relationship state
    const r = this.relationship;
    parts.push(`【关系】信任:${r.trust.toFixed(2)} 熟悉度:${r.familiarity.toFixed(2)}`);

    // User preferences (only if learned)
    const p = this.preferences;
    if (p.communicationStyle !== "unknown" || p.technicalLevel !== "unknown" || p.topics.length > 0) {
      const prefs: string[] = [];
      if (p.topics.length > 0) prefs.push(`话题:${p.topics.slice(-5).join(",")}`);
      if (p.communicationStyle !== "unknown") prefs.push(`风格:${p.communicationStyle}`);
      if (p.technicalLevel !== "unknown") prefs.push(`水平:${p.technicalLevel}`);
      parts.push(`【用户偏好】${prefs.join(" ")}`);
    }

    // Known facts
    if (this.knownFacts.length > 0) {
      const facts = this.knownFacts.slice(-10).map(f => `${f.key}=${f.value}`);
      parts.push(`【已知信息】${facts.join("; ")}`);
    }

    // Recent patterns
    if (this.patterns.frequentRequests.length > 0) {
      parts.push(`【常见请求】${this.patterns.frequentRequests.slice(-5).join(", ")}`);
    }

    return parts.join("\n");
  }

  /** Hot Path: structured state, never narrative prose. */
  formatForHotPath(): string {
    return this.formatForPrompt();
  }

  // ── Consolidation (background, no LLM) ──

  /** Background: consolidate patterns from interaction history. */
  consolidate(): void {
    // Detect frequent request patterns from growth log
    const recentEvents = this.growthLog.slice(-20);
    const requestCounts = new Map<string, number>();
    for (const e of recentEvents) {
      if (e.eventType === "user_request" || e.eventType === "tool_use") {
        const key = e.description.slice(0, 40);
        requestCounts.set(key, (requestCounts.get(key) ?? 0) + 1);
      }
    }
    this.patterns.frequentRequests = [...requestCounts.entries()]
      .filter(([, c]) => c >= 2)
      .map(([k]) => k)
      .slice(-10);

    // Decay trust if no recent interaction
    const idleTime = Date.now() / 1000 - this.relationship.lastInteraction;
    if (idleTime > 3600) {
      this.relationship.trust = Math.max(0, this.relationship.trust - 0.001 * (idleTime / 3600));
    }
  }

  toDict(): Record<string, unknown> {
    return {
      coreIdentity: this.coreIdentity,
      preferences: { ...this.preferences },
      relationship: { ...this.relationship },
      patterns: { ...this.patterns },
      knownFacts: this.knownFacts.slice(-30),
      growthEvents: this.growthLog.slice(-20).map(g => ({
        type: g.eventType, desc: g.description, sig: g.significance, ts: g.timestamp,
      })),
    };
  }
}
