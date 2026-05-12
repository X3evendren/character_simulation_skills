import { MemoryStore, MemoryRecord } from "./store";

export class FrozenSnapshot {
  snapshotText = "";
  frozenAt = 0;
  dirty = false;

  freeze(
    _stores: Record<string, MemoryStore>,
    ltmRecords: MemoryRecord[] | null = null,
    stmRecords: MemoryRecord[] | null = null,
    coreSummary = "",
  ): string {
    const parts = ["【记忆快照】"];
    if (coreSummary) parts.push("核心关系: " + coreSummary);
    for (const r of (ltmRecords ?? []).slice(0, 5)) parts.push("- " + r.content.slice(0, 100));
    for (const r of (stmRecords ?? []).slice(0, 3)) parts.push("- " + r.content.slice(0, 100));
    this.snapshotText = parts.join("\n");
    this.frozenAt = Date.now() / 1000;
    this.dirty = false;
    return this.snapshotText;
  }
  markDirty(): void { this.dirty = true; }
  isStale(): boolean { return this.dirty || (Date.now() / 1000 - this.frozenAt > 3600); }
  formatForPrompt(): string { return this.snapshotText; }
}
