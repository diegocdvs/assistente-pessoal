import { randomUUID } from 'node:crypto';
import { buildWebhookKey, inferEventKey, hashPayload } from './key.mjs';
import { shouldTriggerAlert } from './detection.mjs';

export class WebhookMonitor {
  constructor({ store, notifier, config }) {
    if (!store) throw new Error('WebhookMonitor requires a store.');
    if (!notifier) throw new Error('WebhookMonitor requires a notifier.');
    if (!config) throw new Error('WebhookMonitor requires config.');

    this.store = store;
    this.notifier = notifier;
    this.config = config;
  }

  async recordAttempt(rawEvent) {
    const now = rawEvent.now ? new Date(rawEvent.now) : new Date();
    const eventKey = rawEvent.eventKey || inferEventKey(rawEvent);
    const normalizedEvent = { ...rawEvent, eventKey };
    const key = rawEvent.key || buildWebhookKey(normalizedEvent);

    const attempt = {
      id: rawEvent.requestId || randomUUID(),
      key,
      projectId: rawEvent.projectId || 'unknown_project',
      provider: rawEvent.provider || 'unknown_provider',
      webhookName: rawEvent.webhookName || 'unknown_webhook',
      eventKey,
      attemptAt: now.toISOString(),
      status: rawEvent.status || 'received',
      httpStatus: rawEvent.httpStatus || null,
      errorCode: rawEvent.errorCode || null,
      requestId: rawEvent.requestId || null,
      payloadHash: rawEvent.payload ? hashPayload(rawEvent.payload) : null,
      sourceIpHash: rawEvent.sourceIpHash || null,
      metadata: rawEvent.metadata || {}
    };

    await this.store.saveAttempt(attempt);

    const recentAttempts = await this.store.getRecentAttempts(key, {
      lookbackMinutes: this.config.lookbackMinutes,
      now
    });

    const decision = shouldTriggerAlert(recentAttempts, this.config);
    if (!decision.triggered) {
      return { alerted: false, key, attempt, decision };
    }

    if (await this.store.isInCooldown(key, { now })) {
      return { alerted: false, key, attempt, decision, cooldown: true };
    }

    const first = decision.sequence[0];
    const last = decision.sequence[decision.sequence.length - 1];

    const incident = {
      id: randomUUID(),
      key,
      projectId: attempt.projectId,
      provider: attempt.provider,
      webhookName: attempt.webhookName,
      eventKey: attempt.eventKey,
      firstAttemptAt: first.attemptAt,
      lastAttemptAt: last.attemptAt,
      attemptCount: decision.sequence.length,
      ruleTriggered: decision.rule,
      createdAt: now.toISOString(),
      status: 'open'
    };

    const telegramResult = await this.notifier.sendIncident(incident).catch((error) => ({
      ok: false,
      error: error?.message || String(error)
    }));

    await this.store.createIncident({
      ...incident,
      telegramSentAt: telegramResult.ok ? now.toISOString() : null,
      telegramResult
    });

    await this.store.setCooldown(key, {
      cooldownMinutes: this.config.cooldownMinutes,
      now
    });

    return { alerted: true, key, attempt, incident, telegramResult };
  }
}
