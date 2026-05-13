/** Skill Library — Memento-Skills externalized behavior memory.  */
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";

export interface Skill {
  name: string; title: string; description: string; content: string;
  triggers: string[]; usageCount: number; successCount: number;
  lastUsed: number; createdAt: number; archived: boolean;
  readonly successRate: number;
  readonly utilityScore: number;
}

class SkillImpl implements Skill {
  name = ""; title = ""; description = ""; content = ""; triggers: string[] = [];
  usageCount = 0; successCount = 0; lastUsed = 0; createdAt = 0; archived = false;
  get successRate(): number { return this.usageCount === 0 ? 0.5 : this.successCount / this.usageCount; }
  get utilityScore(): number { return this.successRate * Math.log(1 + this.usageCount); }
}

export class SkillLibrary {
  skillsDir: string;
  private _skills: Map<string, SkillImpl> = new Map();

  constructor(skillsDir = "config/skills") { this.skillsDir = skillsDir; }

  loadFromDisk(): void {
    try {
      // using top-level fs/path imports
      if (!existsSync(this.skillsDir)) { mkdirSync(this.skillsDir, { recursive: true }); this._createDefaults(); return; }
      for (const fn of readdirSync(this.skillsDir)) {
        if (!fn.endsWith(".md")) continue;
        const sk = this._parseFile(join(this.skillsDir, fn), fn);
        if (sk) this._skills.set(sk.name, sk);
      }
    } catch { this._createDefaults(); }
  }

  private _parseFile(fp: string, fn: string): SkillImpl | null {
    try {
      const fs = require("fs"); const text = readFileSync(fp, "utf-8");
      const sk = new SkillImpl(); sk.name = fn.replace(/\.md$/, "");
      const tm = text.match(/^# (.+)/m); if (tm) sk.title = tm[1].trim();
      const trm = text.match(/触发[：:]\s*(.+)/); if (trm) sk.triggers = trm[1].split(/[,，]/).map((t: string) => t.trim());
      const dm = text.match(/描述[：:]\s*(.+)/); if (dm) sk.description = dm[1].trim();
      const rm = text.match(/## 规则\n([\s\S]*?)(?=\n---|\n##|\Z)/);
      sk.content = rm ? rm[1].trim() : text; sk.createdAt = Date.now() / 1000;
      return sk;
    } catch { return null; }
  }

  private _createDefaults(): void {
    const defs: Record<string, string> = {
      communication: "# 沟通\n触发: 对话, 倾听, 沉默\n描述: 如何与用户沟通\n\n## 规则\n- 用户说\"嗯\"或在停顿中——他在思考，不要打断\n- 先确认是否真的理解了对方意思，再回答\n- 回应简短：2-3句话讲清楚",
      coding: "# 编程\n触发: 代码, bug, 错误, 修复\n描述: 如何帮用户写代码\n\n## 规则\n- 先读项目的 CLAUDE.md 了解规范\n- 先理解现有代码再改\n- 只改必须改的部分",
      tools: "# 工具\n触发: 执行, 命令, 文件\n描述: 如何使用工具\n\n## 规则\n- exec_command 前确认路径安全\n- 写文件前先读文件\n- 高危命令需要用户确认",
      learning: "# 学习\n触发: 错误, 失败, 重复, 反馈\n描述: 如何从交互中学习\n\n## 规则\n- 同一错误出现两次——停下来分析原因\n- 用户纠正时——记录这次纠正",
    };
    // using top-level fs/path imports
    for (const [n, c] of Object.entries(defs)) {
      const fp = join(this.skillsDir, `${n}.md`);
      if (!existsSync(fp)) { mkdirSync(this.skillsDir, { recursive: true }); writeFileSync(fp, c, "utf-8"); }
      const sk = this._parseFile(fp, `${n}.md`);
      if (sk) { sk.createdAt = Date.now() / 1000; this._skills.set(sk.name, sk); }
    }
  }

  route(ctx: string, n = 3): Skill[] {
    const active = [...this._skills.values()].filter(s => !s.archived);
    if (!active.length) return [];
    const cl = ctx.toLowerCase();
    const scored: Array<[number, SkillImpl]> = [];
    for (const sk of active) {
      let sc = 0;
      for (const t of sk.triggers) { if (cl.includes(t)) sc += 0.15; }
      for (const w of sk.description.split(/\s+/)) { if (cl.includes(w)) sc += 0.05; }
      sc += sk.utilityScore * 0.3;
      if (Date.now() / 1000 - sk.lastUsed < 3600) sc += 0.2;
      else if (Date.now() / 1000 - sk.lastUsed < 86400) sc += 0.1;
      scored.push([sc, sk]);
    }
    scored.sort((a, b) => b[0] - a[0]);
    return scored.filter(([s]) => s > 0.1).slice(0, n).map(([, s]) => s);
  }

  formatForPrompt(skills: Skill[]): string {
    if (!skills.length) return "";
    return "【行为指南】\n" + skills.map(s => `## ${s.title}\n${s.content}`).join("\n\n");
  }

  recordUsage(name: string, success: boolean): void {
    const s = this._skills.get(name); if (!s) return;
    s.usageCount++; if (success) s.successCount++; s.lastUsed = Date.now() / 1000;
  }

  async evolve(failureCtx: string, failureDesc: string, provider: any): Promise<Skill | null> {
    try {
      const r = await provider.chat([{ role: "user", content: `分析交互失败，生成行为规则。\n情境: ${failureCtx}\n失败: ${failureDesc}\n\n格式:\n# 规则名\n触发: 关键词\n描述: 何时使用\n\n## 规则\n- 具体行为指导` }], 0.3, 500);
      const nc = (r.content ?? "").trim();
      if (!nc.includes("## 规则") || nc.length < 20) return null;
      // using top-level fs/path imports
      const nm = `learned_${Math.floor(Date.now() / 1000)}`;
      const fp = join(this.skillsDir, `${nm}.md`);
      mkdirSync(this.skillsDir, { recursive: true });
      writeFileSync(fp, nc, "utf-8");
      const sk = this._parseFile(fp, `${nm}.md`);
      if (sk) { sk.createdAt = Date.now() / 1000; this._skills.set(sk.name, sk); return sk; }
    } catch { /* ignore */ }
    return null;
  }

  /** Hermes pattern: auto-deprecation. Check all skills for staleness. */
  cleanupStale(): { archived: string[]; warnings: string[] } {
    const now = Date.now() / 1000;
    const archived: string[] = [];
    const warnings: string[] = [];

    for (const [name, sk] of this._skills) {
      if (sk.archived) continue;
      const age = now - sk.lastUsed;
      const daysSinceUse = age / 86400;

      // 60 days unused + low success → archive
      if (daysSinceUse > 60 && sk.successRate < 0.3 && sk.usageCount > 0) {
        sk.archived = true;
        archived.push(name);
      }
      // 30 days unused → warn
      else if (daysSinceUse > 30 && sk.usageCount > 0) {
        warnings.push(`${name}: ${Math.round(daysSinceUse)}天未使用`);
      }
      // Low success rate after sufficient trials → warn
      else if (sk.usageCount >= 10 && sk.successRate < 0.1 && !sk.archived) {
        sk.archived = true;
        archived.push(name);
      }
    }
    return { archived, warnings };
  }

  /** Detect similar skills that could be merged. */
  detectMergeCandidates(): string[][] {
    const active = this.listActive();
    const candidates: string[][] = [];

    for (let i = 0; i < active.length; i++) {
      for (let j = i + 1; j < active.length; j++) {
        const a = active[i], b = active[j];
        // Check trigger overlap
        const overlap = a.triggers.filter(t => b.triggers.includes(t));
        if (overlap.length >= 2) {
          candidates.push([a.name, b.name]);
        }
      }
    }
    return candidates;
  }

  get(name: string): Skill | undefined { return this._skills.get(name); }
  listActive(): Skill[] { return [...this._skills.values()].filter(s => !s.archived); }
  archive(name: string): void { const s = this._skills.get(name); if (s) s.archived = true; }
  get length(): number { return this._skills.size; }
}
