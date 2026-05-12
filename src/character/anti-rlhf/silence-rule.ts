export class SilenceRule {
  static buildIdentityAnchor(c: Record<string, string>): string {
    const n = c.name ?? "助手", e = c.essence ?? "", t = c.traits ?? "";
    return [
      `【角色锚定】你是 ${n}，不是AI助手。行为由人格记忆驱力决定。`,
      `本质: ${e}`, `人格: ${t}`,
      "【行为约束】回应简短。不解释动机。呈现本来面目。",
    ].join("\n");
  }

  static injectPrePrompt(base: string, anchor: string): string {
    return `${anchor}\n\n---\n\n${base}`;
  }

  static detectSafetyRefusal(text: string): string[] {
    const ps = [
      /作为.?AI.{0,10}我不能/g,
      /作为.{0,5}(语言模型|人工智能).{0,10}(不能|无法)/g,
      /我建议你寻求专业/g,
      /请注意安全/g,
    ];
    const m: string[] = [];
    for (const p of ps) {
      const f = text.match(p);
      if (f) m.push(...f);
    }
    return m;
  }
}
