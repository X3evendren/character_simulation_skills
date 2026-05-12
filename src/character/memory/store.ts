export type MemoryType = "episodic" | "semantic" | "procedural";

export interface MemoryRecord {
  recordId: string;
  content: string;
  emotionalSignature: Record<string, number>;
  significance: number;
  eventType: string;
  tags: string[];
  timestamp: number;
  trust: number;
  recallCount: number;
  memoryType: MemoryType;
  confidence: number;      // 0-1, decays without verification
  superseded: boolean;     // old version of a fact
  supersededBy: string | null; // pointer to newer version
  metadata: Record<string, unknown>;
}

export interface ConsolidationReport {
  merged: number;
  promoted: number;
  archived: number;
  conflicts: number;
}

export abstract class MemoryStore {
  abstract store(record: MemoryRecord): Promise<string>;
  abstract recall(query: string, n?: number): Promise<MemoryRecord[]>;
  abstract search(embedding?: number[] | null, filters?: Record<string, unknown> | null, n?: number): Promise<MemoryRecord[]>;
  abstract consolidate(): Promise<ConsolidationReport>;
  abstract forget(): Promise<number>;
  async initialize(): Promise<void> {}
  async onSessionStart(): Promise<void> {}
  async onSessionEnd(): Promise<void> {}
  async shutdown(): Promise<void> {}
  abstract get length(): number;
}

export function createMemoryRecord(opts: Partial<MemoryRecord> = {}): MemoryRecord {
  return {
    recordId: opts.recordId ?? "",
    content: opts.content ?? "",
    emotionalSignature: opts.emotionalSignature ?? {},
    significance: opts.significance ?? 0.5,
    eventType: opts.eventType ?? "unknown",
    tags: opts.tags ?? [],
    timestamp: opts.timestamp ?? Date.now() / 1000,
    trust: opts.trust ?? 1.0,
    recallCount: opts.recallCount ?? 0,
    memoryType: opts.memoryType ?? "episodic",
    confidence: opts.confidence ?? 0.7,
    superseded: opts.superseded ?? false,
    supersededBy: opts.supersededBy ?? null,
    metadata: opts.metadata ?? {},
  };
}

export function createConsolidationReport(): ConsolidationReport {
  return { merged: 0, promoted: 0, archived: 0, conflicts: 0 };
}