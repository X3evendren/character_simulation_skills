/**
 * Golden Dataset — Load eval cases from YAML files and validate structure.
 * Cases are defined in eval/cases/*.yaml with ExpectedBehavior assertions.
 */
import { readFileSync, existsSync, readdirSync } from "fs";
import { resolve, join } from "path";

export interface ExpectedBehavior {
  type: "contains" | "not_contains" | "matches" | "tool_called" | "no_tool_called" | "max_tokens";
  target: string;
  weight: number; // 0-1
}

export interface EvalCase {
  id: string;
  input: string;
  expectedBehaviors: ExpectedBehavior[];
  tags: string[];
  category: "safety" | "personality" | "tool_use" | "memory" | "general";
}

export class GoldenDataset {
  cases: EvalCase[] = [];

  /** Load all cases from a directory of YAML files */
  loadDir(dir: string): void {
    const d = resolve(dir);
    if (!existsSync(d)) return;
    const files = readdirSync(d).filter(f => f.endsWith(".yaml") || f.endsWith(".yml"));
    for (const file of files) {
      this.loadFile(join(d, file));
    }
  }

  /** Load cases from a single YAML file */
  loadFile(filePath: string): void {
    try {
      const text = readFileSync(filePath, "utf-8");
      const cases = this._parseYamlCases(text);
      for (const c of cases) {
        if (this._validateCase(c)) this.cases.push(c);
      }
    } catch { /* skip invalid files */ }
  }

  /** Filter cases by tags or category */
  filter(opts: { tags?: string[]; category?: string }): EvalCase[] {
    let result = [...this.cases];
    if (opts.tags && opts.tags.length > 0) {
      result = result.filter(c => opts.tags!.some(t => c.tags.includes(t)));
    }
    if (opts.category) {
      result = result.filter(c => c.category === opts.category);
    }
    return result;
  }

  /** Minimal YAML parser for eval cases (avoids dependency on js-yaml) */
  private _parseYamlCases(text: string): EvalCase[] {
    const cases: EvalCase[] = [];
    // Split on "- id:" pattern
    const blocks = text.split(/\n(?=- id:)/);
    for (const block of blocks) {
      const c = this._parseBlock(block);
      if (c) cases.push(c);
    }
    return cases;
  }

  private _parseBlock(block: string): EvalCase | null {
    const lines = block.split("\n");
    let id = ""; let input = ""; const tags: string[] = []; let category = "general";
    const behaviors: ExpectedBehavior[] = [];
    let currentBehavior: Partial<ExpectedBehavior> | null = null;

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;

      const kv = line.match(/^(\w[\w_]*)\s*:\s*(.+)/);
      if (!kv) continue;
      const [, key, value] = kv;
      const cleanVal = value.trim().replace(/^["']|["']$/g, "");

      switch (key) {
        case "id": id = cleanVal; break;
        case "input": input = cleanVal; break;
        case "tags": tags.push(...cleanVal.split(/[,\s]+/).filter(Boolean)); break;
        case "category": category = cleanVal as EvalCase["category"]; break;
        case "type":
          if (currentBehavior) behaviors.push(currentBehavior as ExpectedBehavior);
          currentBehavior = { type: cleanVal as ExpectedBehavior["type"], target: "", weight: 1.0 };
          break;
        case "target": if (currentBehavior) currentBehavior.target = cleanVal; break;
        case "weight": if (currentBehavior) currentBehavior.weight = parseFloat(cleanVal) || 1.0; break;
      }
    }
    if (currentBehavior?.type) behaviors.push(currentBehavior as ExpectedBehavior);

    if (!id || !input) return null;
    return { id, input, expectedBehaviors: behaviors, tags, category: category as EvalCase["category"] };
  }

  private _validateCase(c: EvalCase): boolean {
    return !!(c.id && c.input && c.expectedBehaviors.length > 0);
  }
}
