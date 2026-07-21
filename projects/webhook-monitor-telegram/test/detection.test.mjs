import assert from 'node:assert/strict';
import test from 'node:test';
import { findRetrySequence, shouldTriggerAlert } from '../src/detection.mjs';

function attemptsFromOffsets(offsets) {
  const base = new Date('2026-07-21T12:00:00.000Z').getTime();
  return offsets.map((seconds, index) => ({ id: String(index), attemptAt: new Date(base + seconds * 1000).toISOString() }));
}

test('triggers on five consecutive attempts with roughly one minute between each', () => {
  const attempts = attemptsFromOffsets([0, 60, 120, 180, 240]);
  const decision = shouldTriggerAlert(attempts, {
    mode: 'retry_sequence',
    attemptThreshold: 5,
    minGapSeconds: 45,
    maxGapSeconds: 75
  });

  assert.equal(decision.triggered, true);
  assert.equal(decision.sequence.length, 5);
});

test('does not trigger on four attempts', () => {
  const attempts = attemptsFromOffsets([0, 60, 120, 180]);
  const decision = shouldTriggerAlert(attempts, {
    mode: 'retry_sequence',
    attemptThreshold: 5,
    minGapSeconds: 45,
    maxGapSeconds: 75
  });

  assert.equal(decision.triggered, false);
});

test('does not trigger when gaps are outside accepted retry interval', () => {
  const attempts = attemptsFromOffsets([0, 10, 20, 30, 40]);
  const sequence = findRetrySequence(attempts, { minGapSeconds: 45, maxGapSeconds: 75 });
  assert.equal(sequence.length, 1);
});
