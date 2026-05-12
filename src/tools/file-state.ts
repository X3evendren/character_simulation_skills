/** File State Tracker — dedup reads, enforce read-before-write. */

import { existsSync, statSync, readFileSync } from "fs";
import { createHash } from "crypto";

interface FileState {
  path: string;
  mtime: number;
  hash: string;
  lastReadAt: number;
}

export class FileStateTracker {
  private states = new Map<string, FileState>();

  /** Record a file read. Returns true if file was unchanged since last read. */
  recordRead(filePath: string): { unchanged: boolean; content?: string } {
    const abs = this._resolve(filePath);
    if (!existsSync(abs)) return { unchanged: false };

    const stat = statSync(abs);
    const content = readFileSync(abs, "utf-8");
    const hash = createHash("md5").update(content).digest("hex");
    const prev = this.states.get(abs);

    this.states.set(abs, { path: abs, mtime: stat.mtimeMs, hash, lastReadAt: Date.now() });

    if (prev && prev.mtime === stat.mtimeMs && prev.hash === hash) {
      return { unchanged: true, content };
    }
    return { unchanged: false, content };
  }

  /** Check if a file was read before editing. Returns warning message or null. */
  checkReadBeforeWrite(filePath: string): string | null {
    const abs = this._resolve(filePath);
    const prev = this.states.get(abs);
    if (!prev) {
      return `Warning: "${filePath}" has not been read yet. Consider reading it first to understand its current content.`;
    }
    if (!existsSync(abs)) return null;
    const stat = statSync(abs);
    if (stat.mtimeMs > prev.lastReadAt + 1000) {
      return `Warning: "${filePath}" has been modified since you last read it. Re-read to get the latest content.`;
    }
    return null;
  }

  /** Check if a file was previously read (for duplicate read warnings). */
  wasRead(filePath: string): boolean {
    return this.states.has(this._resolve(filePath));
  }

  /** Get the cached content hash for unchanged detection. */
  getHash(filePath: string): string | undefined {
    return this.states.get(this._resolve(filePath))?.hash;
  }

  private _resolve(p: string): string {
    // Simple resolve — caller should pass absolute paths
    return p.replace(/\\/g, "/");
  }
}
