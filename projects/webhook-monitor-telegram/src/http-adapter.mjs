import { createHash } from 'node:crypto';

export function hashIp(ip) {
  if (!ip) return null;
  return createHash('sha256').update(String(ip)).digest('hex').slice(0, 16);
}

export function extractHeaders(request) {
  const headers = {};
  for (const [key, value] of Object.entries(request.headers || {})) {
    headers[key.toLowerCase()] = Array.isArray(value) ? value.join(',') : value;
  }
  return headers;
}

export async function parseJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  if (chunks.length === 0) return {};

  const raw = Buffer.concat(chunks).toString('utf8');
  if (!raw.trim()) return {};

  try {
    return JSON.parse(raw);
  } catch {
    return { _rawBodyParseError: true, _rawBodyPreview: raw.slice(0, 500) };
  }
}

export function createWebhookHandler({ monitor, routeConfig }) {
  return async function webhookHandler(request, response) {
    const payload = await parseJsonBody(request);
    const headers = extractHeaders(request);

    const result = await monitor.recordAttempt({
      projectId: routeConfig.projectId,
      provider: routeConfig.provider,
      webhookName: routeConfig.webhookName,
      payload,
      headers,
      requestId: headers['x-request-id'] || headers['x-correlation-id'],
      sourceIpHash: hashIp(request.socket?.remoteAddress),
      status: 'received',
      metadata: {
        method: request.method,
        url: request.url,
        userAgent: headers['user-agent'] || null
      }
    });

    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ ok: true, monitored: true, alerted: result.alerted }));
  };
}
