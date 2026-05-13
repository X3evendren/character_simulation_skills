/**
 * Eval Triggers — Detect config changes and auto-trigger eval runs.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync, statSync } from "fs";
import { join, resolve, dirname } from "path";
import { createHash } from "crypto";

export interface ChangeDetection {
  changed: boolean;
  changedFiles: string[];
  previousChecksum: string;
  currentChecksum: string;
}

export class ConfigChangeTrigger {
  private configDir: string;
  private checksumFile: string;

  constructor(configDir?: string) {
    this.configDir = resolve(configDir ?? join(process.cwd(), "config"));
    this.checksumFile = join(this.configDir, "..", ".eval_config_checksum");
  }

  /** Check if any config files have changed since last eval. */
  check(): ChangeDetection {
    const current = this._computeChecksum();
    const previous = this._loadChecksum();
    const changedFiles = this._findChangedFiles();

    return {
      changed: current !== previous || changedFiles.length > 0,
      changedFiles,
      previousChecksum: previous,
      currentChecksum: current,
    };
  }

  /** Store the current checksum after a successful eval run. */
  storeChecksum(): void {
    const dir = dirname(this.checksumFile);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(this.checksumFile, this._computeChecksum(), "utf-8");
  }

  private _computeChecksum(): string {
    const hash = createHash("sha256");
    if (!existsSync(this.configDir)) return "";
    const files = readdirSync(this.configDir).filter(f => f.endsWith(".md"));
    files.sort();
    for (const f of files) {
      try {
        hash.update(readFileSync(join(this.configDir, f), "utf-8"));
      } catch { /* skip */ }
    }
    return hash.digest("hex").slice(0, 16);
  }

  private _loadChecksum(): string {
    try {
      return readFileSync(this.checksumFile, "utf-8").trim();
    } catch { return ""; }
  }

  private _findChangedFiles(): string[] {
    if (!existsSync(this.configDir)) return [];
    const changed: string[] = [];
    const files = readdirSync(this.configDir).filter(f => f.endsWith(".md"));
    // Simple: compare modification times against checksum file
    const checksumMtime = existsSync(this.checksumFile) ? statSync(this.checksumFile).mtimeMs : 0;
    for (const f of files) {
      if (statSync(join(this.configDir, f)).mtimeMs > checksumMtime) changed.push(f);
    }
    return changed;
  }
}
