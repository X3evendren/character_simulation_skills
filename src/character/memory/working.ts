import { MemoryStore, MemoryRecord, createMemoryRecord, ConsolidationReport, createConsolidationReport } from "./store";

export class WorkingMemory extends MemoryStore {
  private capacity: number;
  private _records: Map<string, MemoryRecord> = new Map();
  private _order: string[] = [];
  private _locked: Set<string> = new Set();
  private _nextId = 1;

  constructor(capacity = 50) { super(); this.capacity = capacity; }

  get length(): number { return this._records.size; }

  async store(record: MemoryRecord): Promise<string> {
    const rid = record.recordId || "wm_" + (this._nextId++);
    record.recordId = rid;
    this._records.set(rid, record);
    this._order.push(rid);
    if (record.significance >= 0.7) this._locked.add(rid);
    if (this._records.size > this.capacity) this._evict();
    return rid;
  }

  async recall(query: string, n = 5): Promise<MemoryRecord[]> {
    const ql = query.toLowerCase();
    const scored: Array<[number, MemoryRecord]> = [];
    for (const r of this._records.values()) {
      let score = 0;
      const c = r.content.toLowerCase();
      if (c.includes(ql)) score += 0.5;
      for (const kw of ql.split(/\s+/)) { if (c.includes(kw)) score += 0.1; }
      score += r.significance * 0.2;
      if (r.recordId && this._locked.has(r.recordId)) score += 0.2;
      scored.push([score, r]);
    }
    scored.sort((a,b) => b[0] - a[0]);
    return scored.slice(0, n).map(x => x[1]);
  }

  async search(embedding?: number[]|null, filters?: Record<string,any>|null, n = 5): Promise<MemoryRecord[]> {
    if (filters) {
      const results: MemoryRecord[] = [];
      const tags = (filters.tags as string[]) ?? [];
      for (const r of this._records.values()) {
        if (tags.some(t => r.tags.includes(t))) results.push(r);
        else if (filters.eventType && r.eventType === filters.eventType) results.push(r);
      }
      return results.slice(0, n);
    }
    return this._order.slice(-n).map(id => this._records.get(id)!).filter(Boolean);
  }

  async consolidate(): Promise<ConsolidationReport> { return createConsolidationReport(); }

  async forget(): Promise<number> {
    const before = this._records.size;
    const toRemove = Math.max(0, this._records.size - this.capacity);
    let removed = 0;
    for (const rid of this._order) {
      if (removed >= toRemove) break;
      if (!this._locked.has(rid)) {
        this._records.delete(rid); removed++;
      }
    }
    this._order = this._order.filter(id => this._records.has(id));
    return before - this._records.size;
  }

  private _evict(): void {
    const candidates: Array<[number, string]> = [];
    for (const [rid, r] of this._records) {
      if (!this._locked.has(rid)) {
        const score = r.significance + Math.max(...Object.values(r.emotionalSignature), 0);
        candidates.push([score, rid]);
      }
    }
    candidates.sort((a,b) => a[0] - b[0]);
    for (const [_, rid] of candidates.slice(0, Math.max(1, this._records.size - this.capacity))) {
      this._records.delete(rid);
    }
    this._order = this._order.filter(id => this._records.has(id));
  }

  unlock(recordId: string): void { this._locked.delete(recordId); }
  getLocked(): MemoryRecord[] { return [...this._locked].map(id => this._records.get(id)!).filter(Boolean); }

  promoteCandidates(): MemoryRecord[] {
    const result: MemoryRecord[] = [];
    for (const r of this._records.values()) {
      if (r.significance > 0.3 || Math.max(...Object.values(r.emotionalSignature), 0) > 0.4) result.push(r);
    }
    return result;
  }
}