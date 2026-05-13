/** Core Graph Memory — Entity-relation network + BFS. better-sqlite3 for Node.js */
import Database from "better-sqlite3";
import { MemoryStore, MemoryRecord, createMemoryRecord, ConsolidationReport, createConsolidationReport } from "./store";

export class CoreGraphMemory extends MemoryStore {
  private dbPath: string; private maxNodes: number; private maxEdges: number;
  private halfLifeDays: number; private _db: Database | null = null;
  private _indexCache: Map<string, any> = new Map();

  constructor(dbPath = ":memory:", maxNodes = 500, maxEdges = 2000, halfLifeDays = 30) {
    super();
    this.dbPath = dbPath; this.maxNodes = maxNodes; this.maxEdges = maxEdges; this.halfLifeDays = halfLifeDays;
  }

  get length(): number {
    return this._db ? (this._db.prepare("SELECT COUNT(*) as c FROM nodes WHERE superseded=0").get() as any).c : 0;
  }

  async initialize(): Promise<void> {
    this._db = new Database(this.dbPath);
    this._db.pragma("journal_mode = WAL");
    this._db.exec(`CREATE TABLE IF NOT EXISTS nodes (
      node_id TEXT PRIMARY KEY, node_type TEXT DEFAULT 'concept', label TEXT NOT NULL,
      properties TEXT DEFAULT '{}', created_at REAL, updated_at REAL, superseded INTEGER DEFAULT 0
    )`);
    this._db.exec(`CREATE TABLE IF NOT EXISTS edges (
      edge_id INTEGER PRIMARY KEY AUTOINCREMENT, from_id TEXT NOT NULL, to_id TEXT NOT NULL,
      relation TEXT NOT NULL, weight REAL DEFAULT 1.0, timestamp REAL,
      source_event TEXT DEFAULT '', superseded INTEGER DEFAULT 0
    )`);
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)");
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)");
    this._db.exec("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)");
  }

  async store(record: MemoryRecord): Promise<string> {
    const rid = record.recordId || `core_${Date.now()}`;
    const triples = this._extractTriples(record.content);
    const now = Date.now() / 1000;
    for (const [subj, rel, obj] of triples) {
      const sid = this._upsertNode(subj, this._inferType(subj), now);
      const oid = this._upsertNode(obj, this._inferType(obj), now);
      this._addEdge(sid, oid, rel, now, record.content.slice(0, 100));
    }
    this._trim(); return rid;
  }

  querySubgraph(entity: string, depth = 2): any {
    const ck = `${entity}_d${depth}`; if (this._indexCache.has(ck)) return this._indexCache.get(ck)!;
    const nodeRows = this._db!.prepare("SELECT node_id, label, node_type FROM nodes WHERE label LIKE ? AND superseded=0").all(`%${entity}%`) as any[];
    if (!nodeRows.length) return { nodes: [], edges: [], summary: `未找到'${entity}'的相关信息` };
    const nodeIds = nodeRows.map((r: any) => r[0]); const visited = new Set(nodeIds); const relevantEdges: any[] = [];
    let frontier = [...nodeIds];
    for (let d = 0; d < depth && frontier.length; d++) {
      const ph = frontier.map(() => "?").join(",");
      const edgeRows = this._db!.prepare(`SELECT * FROM edges WHERE (from_id IN (${ph}) OR to_id IN (${ph})) AND superseded=0`).all(...frontier, ...frontier) as any[];
      const nf: string[] = [];
      for (const er of edgeRows) { relevantEdges.push(er); if (!visited.has(er[1])) { visited.add(er[1]); nf.push(er[1]); } if (!visited.has(er[2])) { visited.add(er[2]); nf.push(er[2]); } }
      frontier = nf;
    }
    const now = Date.now() / 1000;
    const decayedEdges = relevantEdges.map(er => ({ from: er[1], to: er[2], relation: er[3], weight: Math.max(0.1, er[4] * Math.exp(-(now - er[5]) / (this.halfLifeDays * 86400))), source: er[6] }));
    const nodeData = [...visited].map(nid => { const nr = this._db!.prepare("SELECT node_id, label, node_type FROM nodes WHERE node_id=?").get(nid) as any; return nr ? { id: nr[0], label: nr[1], type: nr[2] } : null; }).filter(Boolean) as any[];
    const summary = decayedEdges.slice(0, 10).map(e => `${nodeData.find(n => n.id === e.from)?.label ?? e.from}与${nodeData.find(n => n.id === e.to)?.label ?? e.to}: ${e.relation}`).join("; ") || "无显著关系";
    const result = { nodes: nodeData, edges: decayedEdges, summary };
    this._indexCache.set(ck, result); if (this._indexCache.size > 100) { for (const k of [...this._indexCache.keys()].slice(0, 20)) this._indexCache.delete(k); }
    return result;
  }

  private _extractTriples(text: string): Array<[string, string, string]> {
    const triples: Array<[string, string, string]> = [];
    for (const m of text.matchAll(/([一-鿿]{1,4})(?:对|向|给|和|跟)([一-鿿]{1,4})/g)) triples.push([m[1], /没|不|拒绝/.test(text) ? "negative_interaction" : "interaction", m[2]]);
    for (const m of text.matchAll(/(?:感到|觉得|很|非常|有点)(开心|难过|悲伤|愤怒|恐惧|焦虑|幸福|失落)/g)) triples.push(["角色", "feels", m[1]]);
    return triples;
  }

  private _upsertNode(label: string, nt: string, now: number): string {
    const nid = `${nt}_${label}`;
    if (this._db!.prepare("SELECT node_id FROM nodes WHERE node_id=?").get(nid)) this._db!.prepare("UPDATE nodes SET updated_at=? WHERE node_id=?").run(now, nid);
    else this._db!.prepare("INSERT INTO nodes VALUES (?,?,?,?,?,?,?)").run(nid, nt, label, "{}", now, now, 0);
    return nid;
  }

  private _addEdge(fid: string, tid: string, rel: string, now: number, src: string): void {
    const ex = this._db!.prepare("SELECT edge_id, weight FROM edges WHERE from_id=? AND to_id=? AND relation=? AND superseded=0").get(fid, tid, rel) as any;
    if (ex) this._db!.prepare("UPDATE edges SET weight=MIN(1.0,?), timestamp=? WHERE edge_id=?").run(ex[1] + 0.2, now, ex[0]);
    else this._db!.prepare("INSERT INTO edges (from_id,to_id,relation,weight,timestamp,source_event) VALUES (?,?,?,?,?,?)").run(fid, tid, rel, 0.5, now, src);
  }

  private _inferType(label: string): string {
    if (["开心","难过","悲伤","愤怒","恐惧","焦虑","幸福","失落","孤独","紧张","失望"].includes(label)) return "emotion";
    return label.length <= 4 && /^[一-鿿]+$/.test(label) ? "person" : "concept";
  }

  private _trim(): void {
    let nc = (this._db!.prepare("SELECT COUNT(*) as c FROM nodes WHERE superseded=0").get() as any).c;
    if (nc > this.maxNodes) this._db!.prepare("UPDATE nodes SET superseded=1 WHERE node_id IN (SELECT node_id FROM nodes WHERE superseded=0 ORDER BY updated_at ASC LIMIT ?)").run(nc - this.maxNodes);
    let ec = (this._db!.prepare("SELECT COUNT(*) as c FROM edges WHERE superseded=0").get() as any).c;
    if (ec > this.maxEdges) this._db!.prepare("UPDATE edges SET superseded=1 WHERE edge_id IN (SELECT edge_id FROM edges WHERE superseded=0 ORDER BY weight ASC LIMIT ?)").run(ec - this.maxEdges);
  }

  async recall(query: string, _n = 5): Promise<MemoryRecord[]> {
    const sg = this.querySubgraph(query, 1);
    return sg.summary ? [createMemoryRecord({ recordId: `core_${Date.now()}`, content: sg.summary, eventType: "graph_query", significance: 0.5 })] : [];
  }

  async search(_e?: number[] | null, filters?: Record<string, unknown> | null, n = 5): Promise<MemoryRecord[]> {
    return this.recall((filters?.query as string) ?? "", n);
  }

  async consolidate(): Promise<ConsolidationReport> { return createConsolidationReport(); }

  async forget(): Promise<number> {
    return this._db!.prepare("UPDATE edges SET superseded=1 WHERE timestamp < ? AND weight < 0.2").run(Date.now() / 1000 - this.halfLifeDays * 86400).changes;
  }
}
