/** Sleep Cycle Metabolism — 3-stage memory consolidation. 1:1 from core/memory/metabolism.py */
import { WorkingMemory } from "./working";
import { ShortTermMemory } from "./short-term";
import { LongTermMemory } from "./long-term";
import { ConsolidationReport, createConsolidationReport } from "./store";
import type { CoreGraphMemory } from "./core-graph";

export interface MetabolismStats {
  daydreamCount: number; quickSleepCount: number; fullSleepCount: number;
  totalMerged: number; totalPromoted: number; totalArchived: number; totalConflicts: number;
  lastDaydream: number; lastQuick: number; lastFull: number;
}

export class SleepCycleMetabolism {
  private working: WorkingMemory;
  private stm: ShortTermMemory;
  private ltm: LongTermMemory;
  private core: CoreGraphMemory | null;
  stats: MetabolismStats;

  constructor(working: WorkingMemory, stm: ShortTermMemory, ltm: LongTermMemory, core: CoreGraphMemory | null = null) {
    this.working = working; this.stm = stm; this.ltm = ltm; this.core = core;
    this.stats = {
      daydreamCount: 0, quickSleepCount: 0, fullSleepCount: 0,
      totalMerged: 0, totalPromoted: 0, totalArchived: 0, totalConflicts: 0,
      lastDaydream: 0, lastQuick: 0, lastFull: 0,
    };
  }

  shouldDaydream(tickCount: number, interval = 10): boolean { return tickCount % interval === 0; }
  shouldQuickSleep(tickCount: number, interval = 50): boolean { return tickCount % interval === 0; }

  async daydream(): Promise<ConsolidationReport> {
    this.stats.daydreamCount++; this.stats.lastDaydream = Date.now() / 1000;
    const report = await this.stm.consolidate();
    this.stats.totalMerged += report.merged;
    return report;
  }

  async quickSleep(): Promise<ConsolidationReport> {
    this.stats.quickSleepCount++; this.stats.lastQuick = Date.now() / 1000;
    const report = createConsolidationReport();

    // WM → STM
    for (const record of this.working.promoteCandidates()) {
      await this.stm.store(record); report.promoted++;
    }

    // STM progressive degradation: oldest 5 records → compressed LTM
    const promoted = await this.stm.promoteToLtm(this.ltm, 5);
    report.promoted += promoted.length;

    // STM candidates → LTM (recall_count ≥ 3)
    for (const record of this.stm.promoteCandidates()) {
      await this.ltm.store(record); report.promoted++;
    }

    const ltmReport = await this.ltm.consolidate();
    report.merged += ltmReport.merged;
    this.stats.totalPromoted += report.promoted;
    this.stats.totalMerged += report.merged;
    return report;
  }

  async fullSleep(): Promise<ConsolidationReport> {
    this.stats.fullSleepCount++; this.stats.lastFull = Date.now() / 1000;
    const report = createConsolidationReport();

    const qr = await this.quickSleep();
    report.promoted += qr.promoted;

    // Confidence decay: old unverified LTM facts lose confidence
    const now = Date.now() / 1000;
    report.archived += this.ltm.decayConfidence(7 * 86400, now); // 7-day half-life
    report.archived += this.ltm.compressOld(30 * 86400, now);    // 30-day old → compressed

    const conflicts = this.ltm.detectContradictions();
    report.conflicts = conflicts.length;
    this.stats.totalConflicts += conflicts.length;

    if (this.core) {
      for (const record of this.ltm.promoteCandidates()) {
        await this.core.store(record); report.promoted++;
      }
    }

    report.archived += await this.working.forget();
    report.archived += await this.stm.forget();
    report.archived += await this.ltm.forget();

    this.stats.totalPromoted += report.promoted;
    this.stats.totalArchived += report.archived;
    return report;
  }
}
