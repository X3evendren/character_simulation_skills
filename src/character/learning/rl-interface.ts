/** RL Interface — Trajectory collection stub. 1:1 from core/learning/rl_interface.py */
export interface TrajectoryStep {
  state: string; action: string; reward: number; nextState: string;
}
export interface Trajectory {
  trajectoryId: string; steps: TrajectoryStep[]; totalReward: number;
  timestamp: number; metadata: Record<string, unknown>;
}

export class RLInterface {
  private minTrajectories: number;
  private _trajectories: Trajectory[] = [];
  private _current: Trajectory | null = null;
  private _counter = 0;

  constructor(mt = 100) { this.minTrajectories = mt; }

  startTrajectory(ctx = ""): void {
    this._counter++;
    this._current = {
      trajectoryId: `traj_${this._counter}_${Math.floor(Date.now() / 1000)}`,
      steps: [], totalReward: 0, timestamp: Date.now() / 1000,
      metadata: { context: ctx.slice(0, 200) },
    };
  }

  addStep(ui: string, ar: string, reward = 0): void {
    if (!this._current) this.startTrajectory();
    const step: TrajectoryStep = {
      state: ui.slice(0, 500), action: ar.slice(0, 500),
      reward: Math.max(-1, Math.min(1, reward)), nextState: "",
    };
    if (reward === 0) step.reward = ar.length > 10 && ar.length < 500 ? 0.1 : -0.1;
    this._current!.steps.push(step);
  }

  endTrajectory(or = 0): void {
    if (this._current && this._current.steps.length) {
      for (const s of this._current.steps) this._current.totalReward += s.reward;
      this._current.totalReward += or;
      this._trajectories.push(this._current);
    }
    this._current = null;
    if (this._trajectories.length > 1000) this._trajectories = this._trajectories.slice(-1000);
  }

  get shouldTriggerFT(): boolean { return this._trajectories.length >= this.minTrajectories; }

  exportJSONL(): string {
    return this._trajectories.flatMap(t =>
      t.steps.filter(s => s.reward > 0).map(s =>
        JSON.stringify({
          messages: [
            { role: "system", content: (t.metadata.context as string) ?? "" },
            { role: "user", content: s.state },
            { role: "assistant", content: s.action },
          ],
          metadata: { reward: s.reward, trajectory_id: t.trajectoryId },
        })
      )
    ).join("\n");
  }

  stats() {
    return {
      totalTrajectories: this._trajectories.length,
      totalSteps: this._trajectories.reduce((s, t) => s + t.steps.length, 0),
      avgReward: this._trajectories.reduce((s, t) => s + t.totalReward, 0) / Math.max(1, this._trajectories.length),
      readyForFT: this.shouldTriggerFT,
    };
  }
}
