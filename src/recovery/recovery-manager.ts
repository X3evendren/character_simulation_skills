/**
 * RecoveryManager — Startup recovery orchestrator.
 *
 * On process start:
 *   1. Check for existing checkpoints
 *   2. If found and interactive: prompt user to resume
 *   3. If resume: load Root State, reconstruct agent context
 *   4. If fresh: clear old checkpoints, start clean
 */
import type { CheckpointManager, CheckpointData, RootState, DerivedState } from "./checkpoint";

export interface RecoveryDecision {
  action: "resume" | "fresh";
  checkpoint?: CheckpointData;
  reason: string;
}

export class RecoveryManager {
  private checkpointManager: CheckpointManager;

  constructor(checkpointManager: CheckpointManager) {
    this.checkpointManager = checkpointManager;
  }

  /** Detect if recovery is possible and decide what to do. */
  detect(): RecoveryDecision {
    const latest = this.checkpointManager.loadLatest();
    if (!latest) {
      return { action: "fresh", reason: "No checkpoint found" };
    }

    const age = Date.now() / 1000 - latest.timestamp;
    if (age > 86400 * 7) {
      // Older than 7 days — stale, start fresh
      return { action: "fresh", reason: `Last checkpoint is ${(age / 86400).toFixed(1)} days old` };
    }

    return {
      action: "resume",
      checkpoint: latest,
      reason: `Found checkpoint from turn ${latest.turnCount} (${(age / 60).toFixed(0)} min ago)`,
    };
  }

  /** Get a formatted summary of the checkpoint for user display. */
  formatSummary(data: CheckpointData): string {
    const age = ((Date.now() / 1000 - data.timestamp) / 60).toFixed(0);
    const history = data.rootState.conversationHistory;
    const lastMessages = history.slice(-3).map(m =>
      `  ${m.role === "user" ? "❯" : " "} ${m.content.slice(0, 80)}`
    ).join("\n");

    return [
      `Checkpoint: turn ${data.turnCount} (${age} min ago)`,
      `Emotion: ${data.derivedState.lastEmotion}  Saturation: ${data.derivedState.saturation.toFixed(2)}`,
      lastMessages ? `Recent:\n${lastMessages}` : "",
    ].filter(Boolean).join("\n");
  }

  /** Resume: return the Root State for prompt reconstruction. */
  resume(data: CheckpointData): { root: RootState; derived: DerivedState } {
    return {
      root: data.rootState,
      derived: data.derivedState,
    };
  }

  /** Start fresh: clear old checkpoints. */
  startFresh(): void {
    this.checkpointManager.clear();
  }
}
