import { loadMonitorConfig } from './config.mjs';
import { WebhookMonitor } from './monitor.mjs';
import { MemoryAttemptStore } from './storage-memory.mjs';
import { TelegramNotifier } from './telegram.mjs';

const sent = [];
const notifier = new TelegramNotifier({
  botToken: 'fake',
  chatId: 'fake',
  fetchImpl: async (_url, request) => {
    sent.push(JSON.parse(request.body));
    return { ok: true, json: async () => ({ ok: true, result: { message_id: 1 } }) };
  }
});

const monitor = new WebhookMonitor({
  store: new MemoryAttemptStore(),
  notifier,
  config: loadMonitorConfig({
    WEBHOOK_ATTEMPT_THRESHOLD: '5',
    WEBHOOK_MIN_GAP_SECONDS: '45',
    WEBHOOK_MAX_GAP_SECONDS: '75',
    WEBHOOK_COOLDOWN_MINUTES: '30'
  })
});

const base = new Date('2026-07-21T12:00:00.000Z');
for (let i = 0; i < 5; i += 1) {
  const result = await monitor.recordAttempt({
    now: new Date(base.getTime() + i * 60_000),
    projectId: 'allpost',
    provider: 'anymarket',
    webhookName: 'transmission_update',
    eventKey: 'content_id_100605943',
    payload: { content: { id: '100605943' } },
    requestId: `smoke-${i}`
  });

  console.log(`attempt ${i + 1}: alerted=${result.alerted}`);
}

console.log(`telegram_messages=${sent.length}`);
