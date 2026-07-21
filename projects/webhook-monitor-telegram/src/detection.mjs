export function asDate(value) {
  return value instanceof Date ? value : new Date(value);
}

export function sortAttempts(attempts) {
  return [...attempts].sort((a, b) => asDate(a.attemptAt).getTime() - asDate(b.attemptAt).getTime());
}

export function findRetrySequence(attempts, { minGapSeconds = 45, maxGapSeconds = 75 } = {}) {
  const sorted = sortAttempts(attempts);
  if (sorted.length === 0) return [];

  let current = [sorted[0]];
  let best = current;

  for (let i = 1; i < sorted.length; i += 1) {
    const previous = asDate(sorted[i - 1].attemptAt).getTime();
    const next = asDate(sorted[i].attemptAt).getTime();
    const gapSeconds = (next - previous) / 1000;

    if (gapSeconds >= minGapSeconds && gapSeconds <= maxGapSeconds) {
      current = [...current, sorted[i]];
    } else {
      current = [sorted[i]];
    }

    if (current.length > best.length) best = current;
  }

  return best;
}

export function findBurstWindow(attempts, { windowSeconds = 60, threshold = 5 } = {}) {
  const sorted = sortAttempts(attempts);

  for (let start = 0; start < sorted.length; start += 1) {
    const startAt = asDate(sorted[start].attemptAt).getTime();
    const window = [];

    for (let end = start; end < sorted.length; end += 1) {
      const endAt = asDate(sorted[end].attemptAt).getTime();
      if ((endAt - startAt) / 1000 <= windowSeconds) {
        window.push(sorted[end]);
      }
    }

    if (window.length >= threshold) return window;
  }

  return [];
}

export function shouldTriggerAlert(attempts, config) {
  if (config.mode === 'burst_window') {
    const sequence = findBurstWindow(attempts, {
      windowSeconds: config.maxGapSeconds || 60,
      threshold: config.attemptThreshold
    });

    return {
      triggered: sequence.length >= config.attemptThreshold,
      sequence,
      rule: 'burst_window'
    };
  }

  const sequence = findRetrySequence(attempts, {
    minGapSeconds: config.minGapSeconds,
    maxGapSeconds: config.maxGapSeconds
  });

  return {
    triggered: sequence.length >= config.attemptThreshold,
    sequence,
    rule: 'retry_sequence'
  };
}
