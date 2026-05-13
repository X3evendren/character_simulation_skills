/** Short-Term Memory — SQLite + FTS5. better-sqlite3 for Node.js */
import Database from "better-sqlite3";
import { MemoryStore, MemoryRecord, createMemoryRecord, ConsolidationReport, createConsolidationReport, type MemoryType } from "./store";

export class ShortTermMemory extends MemoryStore {
  private dbPath: string;
  private maxItems: number;
  private trustDecay: number;
  private _db: Database | null = null;
  private _embeddingFn: ((text: string) => number[]) | null = null;

  constructor(dbPath = ":memory:", maxItems = 200) {
    super();
    this.dbPath = dbPath; this.maxItems = maxItems; this.trustDecay = 0.95;
  }

  get length(): number {
    if (!this._db) return 0;
    return (this._db.prepare("SELECT COUNT(*) as c FROM stm").get() as any).c;
  }

  async initialize(): Promise<void> {
    this._db = new Database(this.dbPath);
    this._db.pragma("journal_mode = WAL");
    this._db.exec(`CREATE TABLE IF NOT EXISTS stm (
      record_id TEXT PRIMARY KEY, content TEXT NOT NULL, emotion TEXT DEFAULT '{}',
      significance REAL DEFAULT 0.5, event_type TEXT DEFAULT 'unknown', tags TEXT DEFAULT '[]',
      timestamp REAL, trust REAL DEFAULT 1.0, recall_count INTEGER DEFAULT 0,
      memory_type TEXT DEFAULT 'episodic', confidence REAL DEFAULT 0.7,
      superseded INTEGER DEFAULT 0, superseded_by TEXT, embedding BLOB
    )`);
    this._db.exec(`CREATE VIRTUAL TABLE IF NOT EXISTS stm_fts USING fts5(
      content, event_type, tags, content=stm, content_rowid=rowid
    )`);
  }

  setEmbeddingFn(fn: (text: string) => number[]): void { this._embeddingFn = fn; }

  async store(record: MemoryRecord): Promise<string> {
    const rid = record.recordId || `stm_${Date.now()}_${this.length}`;
    record.recordId = rid;
    let embBlob: Buffer | null = null;
    if (this._embeddingFn) {
      try { const buf = new Float32Array(this._embeddingFn(record.content)); embBlob = Buffer.from(buf.buffer); } catch { /* */ }
    }
    this._db!.prepare("INSERT OR REPLACE INTO stm VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)").run(
      rid, record.content, JSON.stringify(record.emotionalSignature), record.significance,
      record.eventType, JSON.stringify(record.tags), record.timestamp, record.trust,
      record.recallCount, record.memoryType, record.confidence, record.superseded ? 1 : 0,
      record.supersededBy, embBlob,
    );
    this._trim();
    return rid;
  }

  async recall(query: string, n = 5): Promise<MemoryRecord[]> {
    const sanitized = query.replace(/[.:*"^]/g, " ").trim();
    const ftsQuery = sanitized || query;
    let rows = this._db!.prepare("SELECT rowid FROM stm_fts WHERE stm_fts MATCH ? LIMIT ?").all(ftsQuery, n * 3) as any[];
    if (!rows.length) rows = this._db!.prepare("SELECT rowid FROM stm ORDER BY timestamp DESC LIMIT ?").all(n) as any[];
    const results = rows.map((r: any) =>
      this._rowToRecord(this._db!.prepare("SELECT * FROM stm WHERE rowid=?").get(r.rowid) as any)
    ).filter(Boolean);
    results.sort((a, b) => (b.trust * b.significance) - (a.trust * a.significance));
    return results.slice(0, n);
  }

  async search(_e?: number[] | null, filters?: Record<string, unknown> | null, n = 5): Promise<MemoryRecord[]> {
    return filters?.query ? this.recall(filters.query as string, n) : this.recall("", n);
  }

  async consolidate(): Promise<ConsolidationReport> {
    this._db!.prepare("UPDATE stm SET trust = trust * ?").run(this.trustDecay);
    return createConsolidationReport();
  }

  async forget(): Promise<number> {
    return this._db!.prepare("DELETE FROM stm WHERE trust < 0.1").run().changes;
  }

  recordFeedback(recordId: string, helpful: boolean): void {
    const delta = helpful ? 0.05 : -0.10;
    this._db!.prepare("UPDATE stm SET trust = MAX(0.0, MIN(1.0, trust + ?)) WHERE record_id = ?").run(delta, recordId);
    this._db!.prepare("UPDATE stm SET recall_count = recall_count + 1 WHERE record_id = ?").run(recordId);
  }

  /** Progressive degradation: compress N oldest records to summary, reduce significance. */
  degradeOldest(count: number, summaryPrompt?: string): MemoryRecord[] {
    const rows = this._db!.prepare(
      "SELECT * FROM stm WHERE superseded=0 ORDER BY timestamp ASC LIMIT ?"
    ).all(count) as any[];
    if (!rows.length) return [];

    const records = rows.map((r: any) => this._rowToRecord(r));
    // Reduce significance by 0.3 → fades over multiple degradation passes
    for (const r of records) {
      const newSig = Math.max(0.1, r.significance - 0.3);
      this._db!.prepare(
        "UPDATE stm SET significance=?, content=? WHERE record_id=?"
      ).run(newSig, r.content, r.recordId);
      r.significance = newSig;
    }
    return records;
  }

  /** Move records from STM to LTM, keeping only emotional signature + summary. */
  async promoteToLtm(ltmStore: MemoryStore, count: number): Promise<MemoryRecord[]> {
    const records = this.degradeOldest(count);
    const promoted: MemoryRecord[] = [];
    for (const r of records) {
      // Compress: keep emotional sig + first 150 chars as summary
      const summary = r.content.slice(0, 150);
      const upgraded = createMemoryRecord({
        recordId: r.recordId.replace("stm_", "ltm_"),
        content: summary,
        emotionalSignature: r.emotionalSignature,
        significance: Math.max(0.2, r.significance - 0.2),
        eventType: r.eventType,
        tags: r.tags,
        timestamp: r.timestamp,
        trust: r.trust,
        recallCount: r.recallCount,
        memoryType: "episodic",
        confidence: r.trust * r.significance,
      });
      await ltmStore.store(upgraded);
      promoted.push(upgraded);
    }
    return promoted;
  }

  promoteCandidates(): MemoryRecord[] {
    return (this._db!.prepare("SELECT * FROM stm WHERE recall_count >= 3").all() as any[]).map((r: any) => this._rowToRecord(r));
  }

  private _trim(): void {
    const count = (this._db!.prepare("SELECT COUNT(*) as c FROM stm").get() as any).c;
    if (count > this.maxItems) {
      this._db!.prepare("DELETE FROM stm WHERE rowid IN (SELECT rowid FROM stm ORDER BY trust ASC, timestamp ASC LIMIT ?)").run(count - this.maxItems);
    }
  }

  private _rowToRecord(row: any): MemoryRecord {
    return createMemoryRecord({
      recordId: row[0], content: row[1],
      emotionalSignature: JSON.parse(row[2] || "{}"),
      significance: row[3], eventType: row[4],
      tags: JSON.parse(row[5] || "[]"), timestamp: row[6],
      trust: row[7], recallCount: row[8],
      memoryType: (row[9] as MemoryType) ?? "episodic",
      confidence: row[10] ?? 0.7,
      superseded: !!row[11],
      supersededBy: row[12] ?? null,
      metadata: row[13] ? { embedding: row[13] } : {},
    });
  }
}
