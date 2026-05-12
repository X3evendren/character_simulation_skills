/** Config Loader — Parse config/*.md into typed TS objects. */
import { readFileSync, existsSync, mkdirSync, readdirSync } from "fs";
import { resolve, join } from "path";

export interface AssistantConfig {
  name: string;
  essence: string;
  traits: string;
  rules: string;
  rawText: string;
}

export function loadAssistantConfig(configDir: string): AssistantConfig {
  const fp = resolve(configDir, "assistant.md");
  try {
    const text = readFileSync(fp, "utf-8");
    const nameMatch = text.match(/名字[：:]\s*(.+)/);
    const name = nameMatch ? nameMatch[1].trim() : "林雨";
    const essenceMatch = text.match(/## 核心驱动\n\n([\s\S]*?)(?=\n##|\n---|\Z)/);
    const essence = essenceMatch ? essenceMatch[1].trim().replace(/\n/g, " ") : "";
    const traitsMatch = text.match(/## 人格\n\n([\s\S]*?)(?=\n##|\n---|\Z)/);
    const traits = traitsMatch ? traitsMatch[1].trim().replace(/\n/g, " ") : "";
    const rulesMatch = text.match(/## 行为准则\n\n([\s\S]*?)(?=\n##|\n---|\Z)/);
    const rules = rulesMatch ? rulesMatch[1].trim() : "";
    return { name, essence, traits, rules, rawText: text };
  } catch {
    return { name: "林雨", essence: "", traits: "", rules: "", rawText: "" };
  }
}

export interface ToolDefinition {
  name: string; description: string; riskLevel: string;
  concurrencySafe: boolean; readOnly: boolean; parameters: Record<string, unknown>;
}

export function loadToolDefinitions(configDir: string): ToolDefinition[] {
  const fp = resolve(configDir, "tools.md");
  try {
    const text = readFileSync(fp, "utf-8");
    const tools: ToolDefinition[] = [];
    const sections = text.split(/^## /m).filter(s => s.trim());
    for (const sec of sections) {
      const nameMatch = sec.match(/^(\w+)/);
      if (!nameMatch) continue;
      const name = nameMatch[1];
      const descMatch = sec.match(/描述[：:]\s*(.+)/);
      const riskMatch = sec.match(/风险等级[：:]\s*(.+)/);
      const concurrencyMatch = sec.match(/并发安全[：:]\s*(.+)/);
      const readOnlyMatch = sec.match(/只读[：:]\s*(.+)/);
      tools.push({
        name,
        description: descMatch ? descMatch[1].trim() : "",
        riskLevel: riskMatch ? riskMatch[1].trim().toLowerCase() : "low",
        concurrencySafe: concurrencyMatch ? concurrencyMatch[1].trim() === "true" : true,
        readOnly: readOnlyMatch ? readOnlyMatch[1].trim() === "true" : true,
        parameters: {},
      });
    }
    return tools;
  } catch {
    return [];
  }
}

export interface MemoryConfig {
  workingMemorySize: number;
  shortTermMemorySize: number;
  longTermMemorySize: number;
  coreGraphMaxNodes: number;
  coreGraphMaxEdges: number;
  shortTermHalfLifeDays: number;
  longTermHalfLifeDays: number;
  graphEdgeHalfLifeDays: number;
  trustDecayRate: number;
  daydreamIntervalTicks: number;
  quickSleepIntervalTicks: number;
  defaultRetrievalCount: number;
  semanticWeight: number;
  timeDecayWeight: number;
  significanceWeight: number;
}

export function loadMemoryConfig(configDir: string): MemoryConfig {
  const fp = resolve(configDir, "memory.md");
  const defaults: MemoryConfig = {
    workingMemorySize: 50, shortTermMemorySize: 200, longTermMemorySize: 500,
    coreGraphMaxNodes: 500, coreGraphMaxEdges: 2000,
    shortTermHalfLifeDays: 7, longTermHalfLifeDays: 30, graphEdgeHalfLifeDays: 30,
    trustDecayRate: 0.95, daydreamIntervalTicks: 10, quickSleepIntervalTicks: 50,
    defaultRetrievalCount: 5, semanticWeight: 0.3, timeDecayWeight: 0.3, significanceWeight: 0.4,
  };
  try {
    const text = readFileSync(fp, "utf-8");
    const extract = (key: string): number | undefined => {
      const m = text.match(new RegExp(`${key}[：:]\\s*(\\d+\\.?\\d*)`));
      return m ? parseFloat(m[1]) : undefined;
    };
    const v = extract("working_memory_size"); if (v !== undefined) defaults.workingMemorySize = v;
    const s = extract("short_term_memory_size"); if (s !== undefined) defaults.shortTermMemorySize = s;
    const l = extract("long_term_memory_size"); if (l !== undefined) defaults.longTermMemorySize = l;
    const c = extract("core_graph_max_nodes"); if (c !== undefined) defaults.coreGraphMaxNodes = c;
    const ce = extract("core_graph_max_edges"); if (ce !== undefined) defaults.coreGraphMaxEdges = ce;
    const d = extract("daydream_interval_ticks"); if (d !== undefined) defaults.daydreamIntervalTicks = d;
    const q = extract("quick_sleep_interval_ticks"); if (q !== undefined) defaults.quickSleepIntervalTicks = q;
    const sw = extract("semantic_weight"); if (sw !== undefined) defaults.semanticWeight = sw;
    const tw = extract("time_decay_weight"); if (tw !== undefined) defaults.timeDecayWeight = tw;
    const iw = extract("significance_weight"); if (iw !== undefined) defaults.significanceWeight = iw;
  } catch { /* use defaults */ }
  return defaults;
}

export interface SkillsConfig {
  skillsDir: string;
}

export function ensureSkillsDir(baseDir: string): string {
  const d = resolve(baseDir, "skills");
  if (!existsSync(d)) mkdirSync(d, { recursive: true });
  return d;
}
