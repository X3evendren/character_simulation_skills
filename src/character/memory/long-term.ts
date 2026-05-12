/** Long-Term Memory — SQLite + time decay. better-sqlite3 for Node.js */
import Database from "better-sqlite3";
import { MemoryStore, MemoryRecord, createMemoryRecord, ConsolidationReport, createConsolidationReport } from "./store";

export class LongTermMemory extends MemoryStore {
  private dbPath: string; private maxItems: number; private halfLifeDays: number;
  private _db: Database | null = null;

  constructor(dbPath = ":memory:", maxItems = 500, halfLifeDays = 30) {
    super(); this.dbPath = dbPath; this.maxItems = maxItems; this.halfLifeDays = halfLifeDays;
  }

  get length(): number {
    return this._db ? (this._db.prepare("SELECT COUNT(*) as c FROM ltm WHERE superseded=0").get() as any).c : 0;
  }

  async initialize(): Promise<void> {
    this._db = new Database(this.dbPath);
    this._db.pragma("journal_mode = WAL");
    this._db.exec(`CREATE TABLE IF NOT EXISTS ltm (
      record_id TEXT PRIMARY KEY, content TEXT NOT NULL, emotion TEXT DEFAULT '{}',
      significance REAL DEFAULT 0.5, event_type TEXT DEFAULT 'unknown', tags TEXT DEFAULT '[]',
      timestamp REAL, recall_count INTEGER DEFAULT 0, related_ids TEXT DEFAULT '[]',
      memory_type TEXT DEFAULT 'episodic', confidence REAL DEFAULT 0.7,
      superseded INTEGER DEFAULT 0, superseded_by TEXT, embedding BLOB
    )`);
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_ltm_emotion ON ltm(event_type)");
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_ltm_sig ON ltm(significance)");
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_ltm_conf ON ltm(confidence)");
  }

  async store(record: MemoryRecord): Promise<string> {
    const rid = record.recordId || `ltm_${Date.now()}_${this.length}`;
    record.recordId = rid;
    this._db!.prepare("INSERT OR REPLACE INTO ltm VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)").run(
      rid, record.content, JSON.stringify(record.emotionalSignature), record.significance,
      record.eventType, JSON.stringify(record.tags), record.timestamp, record.recallCount,
      JSON.stringify(record.metadata?.relatedIds ?? []), record.memoryType,
      record.confidence, record.superseded ? 1 : 0, record.supersededBy, null,
    );
    this._trim(); return rid;
  }

  async recall(query: string, n = 5): Promise<MemoryRecord[]> {
    const rows = this._db!.prepare(
      "SELECT * FROM ltm WHERE superseded=0 ORDER BY (significance * confidence) DESC LIMIT ?"
    ).all(n * 5) as any[];
    const now = Date.now() / 1000;
    const scored: Array<[number, MemoryRecord]> = [];
    for (const row of rows) {
      const r = this._rowToRecord(row);
      const ql = query.toLowerCase(); let sem = 0;
      if (r.content.toLowerCase().includes(ql)) sem = 0.3;
      else { const hits = ql.split(/\s+/).filter(kw => r.content.toLowerCase().includes(kw)).length; sem = Math.min(0.3, hits * 0.1); }
      scored.push([r.significance * 0.4 + this._timeDecay(r, now) * 0.3 + sem, r]);
    }
    scored.sort((a, b) => b[0] - a[0]);
    for (const [_, r] of scored.slice(0, n)) this._db!.prepare("UPDATE ltm SET recall_count=recall_count+1 WHERE record_id=?").run(r.recordId);
    return scored.slice(0, n).map(([_, r]) => r);
  }

  async search(_e?: number[] | null, filters?: Record<string, unknown> | null, n = 5): Promise<MemoryRecord[]> {
    return filters?.query ? this.recall(filters.query as string, n) : this.recall("", n);
  }

  async consolidate(): Promise<ConsolidationReport> {
    const report = createConsolidationReport();
    const rows = this._db!.prepare("SELECT record_id, content FROM ltm WHERE superseded=0 ORDER BY timestamp DESC LIMIT 50").all() as any[];
    const seen = new Set<string>();
    for (const row of rows) {
      const rid: string = row[0] ?? row.record_id;
      const content: string = row[1] ?? row.content;
      if (seen.has(content)) {
        this._db!.prepare("UPDATE ltm SET superseded=1 WHERE record_id=?").run(rid);
        report.merged++;
      }
      seen.add(content);
    }
    return report;
  }

  async forget(): Promise<number> {
    return this._db!.prepare("DELETE FROM ltm WHERE timestamp < ? AND significance < 0.3").run(Date.now() / 1000 - this.halfLifeDays * 86400).changes;
  }

  detectContradictions(): Array<Record<string, string>> {
    const rows = this._db!.prepare("SELECT * FROM ltm WHERE superseded=0 ORDER BY timestamp DESC LIMIT 100").all() as any[];
    const conflicts: Array<Record<string, string>> = [];
    for (let i = 0; i < rows.length; i++) {
      for (let j = i + 1; j < rows.length; j++) {
        const e1 = JSON.parse(rows[i][2] || "{}"), e2 = JSON.parse(rows[j][2] || "{}");
        if ((e1.joy > 0.5 && e2.sadness > 0.5) || (e1.trust > 0.5 && e2.fear > 0.5))
          conflicts.push({ recordA: rows[i][0], recordB: rows[j][0], type: "emotional_contradiction" });
      }
    }
    return conflicts;
  }

  promoteCandidates(): MemoryRecord[] {
    return (this._db!.prepare("SELECT * FROM ltm WHERE recall_count>=5 AND significance>=0.8 AND superseded=0").all() as any[]).map((r: any) => this._rowToRecord(r));
  }

  private _timeDecay(r: MemoryRecord, now: number): number { return Math.exp(-(now - r.timestamp) / (this.halfLifeDays * 86400)); }
  private _trim(): void {
    const c = (this._db!.prepare("SELECT COUNT(*) as c FROM ltm").get() as any).c;
    if (c > this.maxItems) this._db!.prepare("DELETE FROM ltm WHERE rowid IN (SELECT rowid FROM ltm ORDER BY significance ASC, timestamp ASC LIMIT ?)").run(c - this.maxItems);
  }
  /** Update confidence — reinforced by recall or contradicted by new evidence. */
  updateConfidence(recordId: string, delta: number): void {
    this._db!.prepare(
      "UPDATE ltm SET confidence = MAX(0.0, MIN(1.0, confidence + ?)) WHERE record_id=?"
    ).run(delta, recordId);
  }

  /** Mark a fact as superseded by a newer version. Never silently delete. */
  markSuperseded(recordId: string, byRecordId: string): void {
    this._db!.prepare(
      "UPDATE ltm SET superseded=1, superseded_by=?, confidence=0.1 WHERE record_id=?"
    ).run(byRecordId, recordId);
  }

  /** Decay confidence of old, unverified facts. */
  decayConfidence(halfLifeSeconds: number, now: number): number {
    const lambda = Math.LN2 / halfLifeSeconds;
    return this._db!.prepare(
      `UPDATE ltm SET confidence = confidence * ?
       WHERE superseded=0 AND recall_count=0 AND confidence > 0.2
       AND (? - timestamp) > ?`
    ).run(Math.exp(-lambda), now, halfLifeSeconds).changes;
  }

  /** Compress old records: full text → short summary + emotional vector. */
  compressOld(minAgeSeconds: number, now: number): number {
    return this._db!.prepare(
      `UPDATE ltm SET significance = significance * 0.5
       WHERE superseded=0 AND confidence < 0.3
       AND (? - timestamp) > ? AND recall_count = 0`
    ).run(now, minAgeSeconds).changes;
  }

  private _rowToRecord(row: any): MemoryRecord {
    return createMemoryRecord({
      recordId: row[0], content: row[1],
      emotionalSignature: JSON.parse(row[2] || "{}"),
      significance: row[3], eventType: row[4],
      tags: JSON.parse(row[5] || "[]"), timestamp: row[6],
      recallCount: row[7],
      memoryType: (row[9] as any) ?? "episodic",
      confidence: row[10] ?? 0.7,
      superseded: !!row[11],
      supersededBy: row[12] ?? null,
      metadata: { relatedIds: JSON.parse(row[8] || "[]"), embedding: row[13] },
    });
  }
}
