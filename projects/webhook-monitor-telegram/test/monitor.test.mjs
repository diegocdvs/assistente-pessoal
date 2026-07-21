import assert from 'node:assert/strict';
import test from 'node:test';
import { loadMonitorConfig } from '../src/config.mjs';
import { WebhookMonitor } from '../src/monitor.mjs';
import { MemoryAttemptStore } from '../src/storage-memory.mjs';
import { TelegramNotifier } from '../src/telegram.mjs';

function fakeNotifier(sent) {
  return new TelegramNotifier({
    botToken: 'fake-token',
    chatId: 'fake-chat',
    fetchImpl: async (_url, request) => {
      sent.push(JSON.parse(request.body));
      return { ok: true, json: async () => ({ ok: true, result: { message_id: sent.length } }) };
    }
  });
}

test('sends one Telegram message on fifth qualifying attempt', async () => {
  const sent = [];
  const monitor = new WebhookMonitor({
    store: new MemoryAttemptStore(),
    notifier: fakeNotifier(sent),
    config: loadMonitorConfig({
      WEBHOOK_ATTEMPT_THRESHOLD: '5',
      WEBHOOK_MIN_GAP_SECONDS: '45',
      WEBHOOK_MAX_GAP_SECONDS: '75',
      WEBHOOK_LOOKBACK_MINUTES: '10',
      WEBHOOK_COOLDOWN_MINUTES: '30'
    })
  });

  const base = new Date('2026-07-21T12:00:00.000Z');
  let lastResult;

  for (let i = 0; i < 5; i += 1) {
    lastResult = await monitor.recordAttempt({
      now: new Date(base.getTime() + i * 60_000),
      projectId: 'allpost',
      provider: 'anymarket',
      webhookName: 'transmission_update',
      eventKey: 'content_id_100605943',
      payload: { content: { id: '100605943' } },
      requestId: `req-${i}`
    });
  }

  assert.equal(lastResult.alerted, true);
  assert.equal(sent.length, 1);
  assert.match(sent[0].text, /Alerta de Webhook/);
});

test('cooldown prevents repeated Telegram spam', async () => {
  const sent = [];
  const monitor = new WebhookMonitor({
    store: new MemoryAttemptStore(),
    notifier: fakeNotifier(sent),
    config: loadMonitorConfig({
      WEBHOOK_ATTEMPT_THRESHOLD: '5',
      WEBHOOK_MIN_GAP_SECONDS: '45',
      WEBHOOK_MAX_GAP_SECONDS: '75',
      WEBHOOK_LOOKBACK_MINUTES: '10',
      WEBHOOK_COOLDOWN_MINUTES: '30'
    })
  });

  const base = new Date('2026-07-21T12:00:00.000Z');

  for (let i = 0; i < 7; i += 1) {
    await monitor.recordAttempt({
      now: new Date(base.getTime() + i * 60_000),
      projectId: 'allpost',
      provider: 'anymarket',
      webhookName: 'transmission_update',
      eventKey: 'content_id_100605943',
      payload: { content: { id: '100605943' } },
      requestId: `req-${i}`
    });
  }

  assert.equal(sent.length, 1);
});
