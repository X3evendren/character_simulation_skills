export interface ConsciousContent {
  kind: string;
  content: string;
  salience: number;
  source: string;
  timestamp: number;
}

export function createConsciousContent(kind: string, content: string, source = ''): ConsciousContent {
  return { kind, content, salience: 0, source, timestamp: 0 };
}

export function scoreSalience(
  candidates: ConsciousContent[],
  driveVector?: Record<string, number>,
  predictionError = 0,
): ConsciousContent[] {
  const now = Date.now() / 1000;
  for (const item of candidates) {
    item.timestamp = now;
    let emotionScore = 0;
    if (item.kind === 'emotion' || item.kind === 'threat') emotionScore = 0.7;
    else if (item.kind === 'defense') emotionScore = 0.5;
    else if (item.kind === 'response') emotionScore = 0.4;
    let driveScore = 0;
    if (driveVector) {
      const lower = item.content.toLowerCase();
      if (driveVector.curiosity && /[问题探索发现学习]/.test(lower))
        driveScore = driveVector.curiosity;
      if (driveVector.connection && /[用户关系理解感受]/.test(lower))
        driveScore = Math.max(driveScore, driveVector.connection);
      if (driveVector.helpfulness && /[任务帮助解决完成]/.test(lower))
        driveScore = Math.max(driveScore, driveVector.helpfulness);
    }
    item.salience = emotionScore * 0.35 + driveScore * 0.25 + predictionError * 0.2 + 0.5 * 0.2;
    item.salience = Math.max(0, Math.min(1.0, item.salience));
  }
  return candidates;
}

export function updateWorkspace(
  candidates: ConsciousContent[], capacity = 4, threshold = 0.3,
): ConsciousContent[] {
  return candidates.filter(c => c.salience >= threshold)
    .sort((a, b) => b.salience - a.salience).slice(0, capacity);
}
