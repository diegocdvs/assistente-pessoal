import { createHash } from 'node:crypto';

export function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;

  return `{${Object.keys(value)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
    .join(',')}}`;
}

export function sha256Short(value, length = 20) {
  return createHash('sha256').update(String(value)).digest('hex').slice(0, length);
}

export function hashPayload(payload) {
  return sha256Short(stableStringify(payload), 32);
}

export function normalizePart(value, fallback = 'unknown') {
  const text = String(value ?? '').trim();
  return text.length > 0 ? text.replace(/\s+/g, '_').toLowerCase() : fallback;
}

export function inferEventKey({ payload = {}, headers = {}, requestId = '' } = {}) {
  const directCandidates = [
    payload.event_id,
    payload.eventId,
    payload.id,
    payload.transmission_id,
    payload.transmissionId,
    payload.content_id,
    payload.contentId,
    payload.content?.id,
    payload.order_id,
    payload.orderId,
    payload.item_id,
    payload.itemId,
    payload.model_id,
    payload.modelId,
    headers['x-event-id'],
    headers['x-request-id'],
    requestId
  ];

  const direct = directCandidates.find((candidate) => candidate !== undefined && candidate !== null && String(candidate).trim() !== '');
  if (direct) return normalizePart(direct, 'event');

  return `payload_${hashPayload(payload)}`;
}

export function buildWebhookKey(event) {
  const projectId = normalizePart(event.projectId, 'project');
  const provider = normalizePart(event.provider, 'provider');
  const webhookName = normalizePart(event.webhookName, 'webhook');
  const eventKey = normalizePart(event.eventKey || inferEventKey(event), 'event');

  return `${projectId}:${provider}:${webhookName}:${eventKey}`;
}
