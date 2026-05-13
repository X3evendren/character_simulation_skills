/** Archive Memory — Final resting place for superseded/expired memories.
 *  Timeline-only retrieval. TTL hard deletion is the ONLY deletion path.
 *


 */
import Database from "better-sqlite3";
import { MemoryStore, MemoryRecord, createMemoryRecord, ConsolidationReport, createConsolidationReport } from "./store";

export class ArchiveMemory extends MemoryStore {
  private dbPath: string;
  private maxItems: number;
  private ttlSeconds: number;
  private _db: Database | null = null;

  constructor(dbPath = ":memory:", maxItems = 2000, ttlDays = 90) {
    super();
    this.dbPath = dbPath;
    this.maxItems = maxItems;
    this.ttlSeconds = ttlDays * 86400;
  }

  get length(): number {
    if (!this._db) return 0;
    return (this._db.prepare("SELECT COUNT(*) as c FROM archive").get() as any).c;
  }

  async initialize(): Promise<void> {
    this._db = new Database(this.dbPath);
    this._db.pragma("journal_mode = WAL");
    this._db.exec(`CREATE TABLE IF NOT EXISTS archive (
      record_id TEXT PRIMARY KEY, content TEXT NOT NULL, emotion TEXT DEFAULT '{}',
      significance REAL DEFAULT 0.5, event_type TEXT DEFAULT 'unknown', tags TEXT DEFAULT '[]',
      timestamp REAL, archived_at REAL, ttl REAL, recall_count INTEGER DEFAULT 0,
      original_layer TEXT DEFAULT 'ltm'
    )`);
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_archive_ttl ON archive(ttl)");
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_archive_ts ON archive(timestamp)");
  }

  async store(record: MemoryRecord): Promise<string> {
    const rid = record.recordId || `arc_${Date.now()}_${this.length}`;
    record.recordId = rid;
    const now = Date.now() / 1000;
    this._db!.prepare("INSERT OR REPLACE INTO archive VALUES (?,?,?,?,?,?,?,?,?,?,?)").run(
      rid, record.content, JSON.stringify(record.emotionalSignature),
      record.significance, record.eventType, JSON.stringify(record.tags),
      record.timestamp, now, now + this.ttlSeconds, record.recallCount,
      record.metadata?.originalLayer ?? "ltm",
    );
    this._trim();
    return rid;
  }

  /** Timeline-only retrieval — by time range. No semantic search. */
  async recall(query: string, n = 5): Promise<MemoryRecord[]> {
    // Only time-based queries; ignore semantic query text
    return this.getRecent(n);
  }

  async search(_e?: number[] | null, filters?: Record<string, unknown> | null, n = 5): Promise<MemoryRecord[]> {
    const from = (filters?.from as number) ?? 0;
    const to = (filters?.to as number) ?? (Date.now() / 1000);
    const rows = this._db!.prepare(
      "SELECT * FROM archive WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC LIMIT ?"
    ).all(from, to, n) as any[];
    return rows.map((r: any) => this._rowToRecord(r));
  }

  getRecent(n = 20): MemoryRecord[] {
    if (!this._db) return [];
    const rows = this._db!.prepare(
      "SELECT * FROM archive ORDER BY timestamp DESC LIMIT ?"
    ).all(n) as any[];
    return rows.map((r: any) => this._rowToRecord(r));
  }

  async consolidate(): Promise<ConsolidationReport> {
    return createConsolidationReport();
  }

  /** TTL hard deletion — the ONLY deletion path for archived memories. */
  async forget(): Promise<number> {
    if (!this._db) return 0;
    const now = Date.now() / 1000;
    return this._db!.prepare(
      "DELETE FROM archive WHERE ttl < ?"
    ).run(now).changes;
  }

  /** Move superseded LTM records to archive. */
  async absorbSuperseded(ltm: MemoryStore): Promise<number> {
    // LTM stores superseded records; they're not automatically moved
    // This is called periodically to sweep superseded LTM into archive
    const recent = await ltm.search(null, { superseded: true }, 100);
    let count = 0;
    for (const r of recent) {
      if (r.superseded) {
        await this.store(r);
        count++;
      }
    }
    return count;
  }

  /** Force remove specific records by IDs. */
  async purge(recordIds: string[]): Promise<number> {
    let count = 0;
    for (const id of recordIds) {
      const result = this._db!.prepare("DELETE FROM archive WHERE record_id = ?").run(id);
      count += result.changes;
    }
    return count;
  }

  private _trim(): void {
    const count = (this._db!.prepare("SELECT COUNT(*) as c FROM archive").get() as any).c;
    if (count > this.maxItems) {
      this._db!.prepare(
        "DELETE FROM archive WHERE record_id IN (SELECT record_id FROM archive ORDER BY ttl ASC, significance ASC LIMIT ?)"
      ).run(count - this.maxItems);
    }
  }

  private _rowToRecord(row: any): MemoryRecord {
    return createMemoryRecord({
      recordId: row[0], content: row[1],
      emotionalSignature: JSON.parse(row[2] || "{}"),
      significance: row[3], eventType: row[4],
      tags: JSON.parse(row[5] || "[]"), timestamp: row[6],
      recallCount: row[8],
      metadata: { archivedAt: row[7], ttl: row[9], originalLayer: row[10] },
    });
  }
}
