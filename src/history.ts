/**
 * History Store — File persistence + Ctrl+R search. Copied from nanobot SafeFileHistory.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { join } from "path";
import { homedir } from "os";

export class HistoryStore {
  private entries: string[] = [];
  private filePath: string;
  private maxEntries: number;
  private cursor: number = -1; // -1 = at bottom (newest), >=0 = position

  constructor(filePath?: string, maxEntries = 500) {
    this.filePath = filePath ?? join(homedir(), ".character_mind_history");
    this.maxEntries = maxEntries;
    this._load();
  }

  private _load(): void {
    try {
      if (existsSync(this.filePath)) {
        const text = readFileSync(this.filePath, "utf-8");
        this.entries = text.split("\n").filter(Boolean).slice(-this.maxEntries);
      }
    } catch { /* ignore */ }
  }

  private _save(): void {
    try {
      const dir = this.filePath.replace(/[\\/][^\\/]+$/, "");
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
      writeFileSync(this.filePath, this.entries.join("\n") + "\n", "utf-8");
    } catch { /* ignore */ }
  }

  /** Add entry. Skips duplicates of the most recent entry. */
  add(entry: string): void {
    const trimmed = entry.trim();
    if (!trimmed) return;
    if (this.entries.length > 0 && this.entries[this.entries.length - 1] === trimmed) return;
    this.entries.push(trimmed);
    if (this.entries.length > this.maxEntries) this.entries = this.entries.slice(-this.maxEntries);
    this.cursor = -1;
    this._save();
  }

  /** Navigate up (older entries). Returns the entry or null. */
  up(): string | null {
    if (this.entries.length === 0) return null;
    if (this.cursor === -1) this.cursor = this.entries.length - 1;
    else this.cursor = Math.max(0, this.cursor - 1);
    return this.entries[this.cursor];
  }

  /** Navigate down (newer entries). Returns the entry or null. */
  down(): string | null {
    if (this.entries.length === 0 || this.cursor === -1) return null;
    this.cursor++;
    if (this.cursor >= this.entries.length) { this.cursor = -1; return null; }
    return this.entries[this.cursor];
  }

  /** Reset cursor to bottom */
  resetCursor(): void { this.cursor = -1; }

  /** Whether cursor is at the newest position (not navigating history) */
  get atNewest(): boolean { return this.cursor === -1; }

  /** Search entries containing query (case-insensitive). Returns matching entries. */
  search(query: string): string[] {
    if (!query.trim()) return [];
    const lower = query.toLowerCase();
    return this.entries.filter(e => e.toLowerCase().includes(lower)).slice(-20).reverse();
  }

  get length(): number { return this.entries.length; }
}
