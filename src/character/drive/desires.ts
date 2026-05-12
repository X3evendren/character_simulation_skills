/**
 * Drive System — Five intrinsic drives + reward system.
 * 1:1 translation from core/drive/desires.py
 *
 * Drives: curiosity / helpfulness / achievement / connection / autonomy
 * Unsatisfied drives rise over time; satisfaction events reduce them.
 * Above threshold → proactive initiative behavior.
 */

export interface DesireData {
  name: string;
  intensity: number;
  baseline: number;
  decayRate: number;
  satisfactionRate: number;
  threshold: number;
  lastSatisfied: number;
}

export function createDesire(
  name: string,
  baseline: number = 0.5,
  threshold: number = 0.7,
  decayRate: number = 0.01,
  satisfactionRate: number = 0.15,
): DesireData {
  return {
    name,
    intensity: baseline,
    baseline,
    decayRate,
    satisfactionRate,
    threshold,
    lastSatisfied: 0,
  };
}

export function desireTick(d: DesireData, dtMinutes: number): void {
  if (d.intensity < d.threshold) {
    d.intensity = Math.min(1.0, d.intensity + d.decayRate * dtMinutes);
  }
}

export function desireSatisfy(d: DesireData, amount: number = 0.15): void {
  d.intensity = Math.max(0.1, d.intensity - amount);
  d.lastSatisfied = Date.now() / 1000;
}

export function desireFrustrate(d: DesireData, amount: number = 0.05): void {
  d.intensity = Math.min(1.0, d.intensity + amount);
}

export function desireIsUrgent(d: DesireData): boolean {
  return d.intensity >= d.threshold;
}

export interface RewardEvent {
  timestamp: number;
  eventType: string;
  valence: number;
  description: string;
  affectedDrives: string[];
}

export class DriveState {
  desires: Record<string, DesireData>;
  rewardHistory: RewardEvent[];
  lastUpdate: number;

  constructor() {
    this.desires = {
      curiosity: createDesire('curiosity', 0.55, 0.7),
      helpfulness: createDesire('helpfulness', 0.65, 0.75),
      achievement: createDesire('achievement', 0.5, 0.7),
      connection: createDesire('connection', 0.45, 0.65),
      autonomy: createDesire('autonomy', 0.4, 0.6),
    };
    this.rewardHistory = [];
    this.lastUpdate = 0;
  }

  tick(dtSeconds: number): void {
    const dtMinutes = dtSeconds / 60;
    this.lastUpdate = Date.now() / 1000;
    for (const d of Object.values(this.desires)) {
      desireTick(d, dtMinutes);
    }
  }

  applyReward(eventType: string, valence: number, description: string = ''): void {
    const d = this.desires;

    if (eventType === 'user_praise') {
      desireSatisfy(d.connection, 0.2);
      desireSatisfy(d.helpfulness, 0.15);
    } else if (eventType === 'task_success') {
      desireSatisfy(d.achievement, 0.2);
      desireSatisfy(d.helpfulness, 0.1);
    } else if (eventType === 'learning') {
      desireSatisfy(d.curiosity, 0.25);
    } else if (eventType === 'connection') {
      desireSatisfy(d.connection, 0.2);
    } else if (eventType === 'error' || eventType === 'failure') {
      desireFrustrate(d.achievement, 0.1);
      desireFrustrate(d.autonomy, 0.05);
    } else if (eventType === 'long_idle') {
      desireFrustrate(d.connection, 0.15);
      desireFrustrate(d.curiosity, 0.1);
    }

    // Universal: positive events slightly satisfy all, negative slightly frustrate
    for (const desire of Object.values(d)) {
      if (valence > 0.3) desireSatisfy(desire, 0.03);
      else if (valence < -0.3) desireFrustrate(desire, 0.02);
    }

    this.rewardHistory.push({
      timestamp: Date.now() / 1000,
      eventType,
      valence,
      description,
      affectedDrives: Object.keys(d),
    });
    if (this.rewardHistory.length > 100) this.rewardHistory = this.rewardHistory.slice(-100);
  }

  shouldTakeInitiative(): DesireData[] {
    const urgent = Object.values(this.desires).filter(d => desireIsUrgent(d));
    urgent.sort((a, b) => b.intensity - a.intensity);
    return urgent.slice(0, 1);
  }

  getInitiativePrompt(desire: DesireData): string {
    const prompts: Record<string, string> = {
      curiosity: '你注意到一些你还不了解的事。主动问一个问题来了解更多。',
      helpfulness: '你发现你可以帮用户做某件事。主动提出帮助。',
      connection: '你有一段时间没有和用户建立深入连接了。用一个微小的关心表达你在。',
      achievement: '你有一个未完成的任务。检查进度并提出下一步。',
      autonomy: '你有一个自己的想法。用一种温和的方式表达你的独立判断。',
    };
    return prompts[desire.name] ?? '';
  }

  getDominantDrive(): DesireData | null {
    const all = Object.values(this.desires);
    if (all.length === 0) return null;
    return all.reduce((a, b) => a.intensity > b.intensity ? a : b);
  }

  getDriveVector(): Record<string, number> {
    const vec: Record<string, number> = {};
    for (const [name, d] of Object.entries(this.desires)) {
      vec[name] = d.intensity;
    }
    return vec;
  }

  toDict(): Record<string, unknown> {
    const d: Record<string, unknown> = {};
    for (const [name, desire] of Object.entries(this.desires)) {
      d[name] = {
        name: desire.name,
        intensity: Math.round(desire.intensity * 1000) / 1000,
        threshold: desire.threshold,
        urgent: desireIsUrgent(desire),
      };
    }
    return { desires: d, lastUpdate: this.lastUpdate };
  }

  static fromDict(data: Record<string, any>): DriveState {
    const ds = new DriveState();
    if (data.desires) {
      for (const [name, ddata] of Object.entries(data.desires) as [string, any][]) {
        if (name in ds.desires) {
          ds.desires[name].intensity = ddata.intensity ?? 0.5;
          ds.desires[name].lastSatisfied = ddata.lastSatisfied ?? 0;
        }
      }
    }
    ds.lastUpdate = data.lastUpdate ?? 0;
    return ds;
  }
}
