/**
 * CheckpointManager — Semantic checkpointing with Root/Derived State distinction.
 *
 * Root State (persisted): what the LLM sees — system prompt, memory, ground truth.
 * Derived State (recomputed): psychology, params, drives, narratives, residue.
 *
 * Checkpoints are written on turn boundaries. On crash, the system can resume
 * from the last Root State and recompute Derived State on the first new turn.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync, unlinkSync } from "fs";
import { join, resolve } from "path";
import { createHash } from "crypto";

export interface RootState {
  /** Last generated system prompt */
  systemPrompt: string;
  /** Formatted memory snapshot text */
  memorySnapshot: string;
  /** Ground truth facts (serializable) */
  groundTruthFacts: string[];
  /** Recent conversation turns: [{ role, content }] */
  conversationHistory: Array<{ role: "user" | "assistant"; content: string }>;
}

export interface DerivedState {
  /** Emotional residue vector */
  affectiveResidue: { warmth: number; weight: number; clarity: number; tension: number };
  /** Current self-narrative */
  selfNarrative: string;
  /** Dominant emotion from last psych analysis */
  lastEmotion: string;
  /** Saturation level */
  saturation: number;
  /** Turn count */
  turnCount: number;
}

export interface CheckpointData {
  checkpointId: string;
  timestamp: number;
  turnCount: number;
  rootState: RootState;
  derivedState: DerivedState;
  version: number;
  checksum: string;
}

const CHECKPOINT_VERSION = 1;
const MAX_CHECKPOINTS = 20;

export class CheckpointManager {
  private dir: string;
  /** In-memory conversation history since last checkpoint */
  private pendingHistory: RootState["conversationHistory"] = [];
  private lastRootState: RootState | null = null;

  constructor(dir?: string) {
    this.dir = resolve(dir ?? join(process.cwd(), "checkpoints"));
  }

  // ═══════════════════════════════════════
  // Public API
  // ═══════════════════════════════════════

  /** Record a user message for the next checkpoint. */
  recordUserMessage(content: string): void {
    this.pendingHistory.push({ role: "user", content });
  }

  /** Record an assistant response for the next checkpoint. */
  recordAssistantMessage(content: string): void {
    this.pendingHistory.push({ role: "assistant", content });
  }

  /** Save a checkpoint (called at turn boundaries). */
  save(root: RootState, derived: DerivedState): string {
    if (!existsSync(this.dir)) mkdirSync(this.dir, { recursive: true });

    // Merge pending history into root
    root.conversationHistory = [
      ...(this.lastRootState?.conversationHistory ?? []),
      ...this.pendingHistory,
    ].slice(-50); // keep last 50 turns max
    this.pendingHistory = [];

    const data: Omit<CheckpointData, "checksum"> = {
      checkpointId: `ckpt_${root.conversationHistory.length}_${Date.now()}`,
      timestamp: Date.now() / 1000,
      turnCount: derived.turnCount,
      rootState: root,
      derivedState: derived,
      version: CHECKPOINT_VERSION,
    };

    const checksum = this._computeChecksum(data);
    const full: CheckpointData = { ...data, checksum };

    const filePath = join(this.dir, `${full.checkpointId}.json`);
    writeFileSync(filePath, JSON.stringify(full, null, 2), "utf-8");

    this.lastRootState = root;
    this._prune();
    return filePath;
  }

  /** Load the latest valid checkpoint. Returns null if none exists. */
  loadLatest(): CheckpointData | null {
    if (!existsSync(this.dir)) return null;

    const files = readdirSync(this.dir)
      .filter(f => f.startsWith("ckpt_") && f.endsWith(".json"))
      .sort()
      .reverse();

    for (const file of files) {
      try {
        const content = readFileSync(join(this.dir, file), "utf-8");
        const data = JSON.parse(content) as CheckpointData;
        if (this._verify(data)) return data;
      } catch { /* corrupt file, try next */ }
    }
    return null;
  }

  /** Load a specific checkpoint by turn count. */
  loadByTurn(turnCount: number): CheckpointData | null {
    if (!existsSync(this.dir)) return null;
    const files = readdirSync(this.dir).filter(f => f.startsWith("ckpt_") && f.endsWith(".json"));
    for (const file of files) {
      try {
        const content = readFileSync(join(this.dir, file), "utf-8");
        const data = JSON.parse(content) as CheckpointData;
        if (data.turnCount === turnCount && this._verify(data)) return data;
      } catch { /* skip */ }
    }
    return null;
  }

  /** List available checkpoints (newest first). */
  list(): Array<{ id: string; turnCount: number; timestamp: number }> {
    if (!existsSync(this.dir)) return [];
    return readdirSync(this.dir)
      .filter(f => f.startsWith("ckpt_") && f.endsWith(".json"))
      .map(f => {
        try {
          const data = JSON.parse(readFileSync(join(this.dir, f), "utf-8")) as CheckpointData;
          return { id: data.checkpointId, turnCount: data.turnCount, timestamp: data.timestamp };
        } catch { return null; }
      })
      .filter((x): x is NonNullable<typeof x> => x !== null)
      .sort((a, b) => b.turnCount - a.turnCount);
  }

  /** Delete all checkpoints. */
  clear(): void {
    if (!existsSync(this.dir)) return;
    const files = readdirSync(this.dir).filter(f => f.startsWith("ckpt_") && f.endsWith(".json"));
    for (const f of files) unlinkSync(join(this.dir, f));
    this.pendingHistory = [];
    this.lastRootState = null;
  }

  get pendingCount(): number { return this.pendingHistory.length; }

  // ═══════════════════════════════════════
  // Internal
  // ═══════════════════════════════════════

  private _computeChecksum(data: Omit<CheckpointData, "checksum">): string {
    const hash = createHash("sha256");
    hash.update(JSON.stringify({ ...data, checksum: "" }));
    return hash.digest("hex").slice(0, 16);
  }

  private _verify(data: CheckpointData): boolean {
    if (data.version !== CHECKPOINT_VERSION) return false;
    const expected = this._computeChecksum({
      checkpointId: data.checkpointId,
      timestamp: data.timestamp,
      turnCount: data.turnCount,
      rootState: data.rootState,
      derivedState: data.derivedState,
      version: data.version,
    });
    return expected === data.checksum;
  }

  private _prune(): void {
    if (!existsSync(this.dir)) return;
    const files = readdirSync(this.dir)
      .filter(f => f.startsWith("ckpt_") && f.endsWith(".json"))
      .sort(); // oldest first
    while (files.length > MAX_CHECKPOINTS) {
      const oldest = files.shift()!;
      try { unlinkSync(join(this.dir, oldest)); } catch { /* ignore */ }
    }
  }
}
