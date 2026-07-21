import { createServer } from 'node:http';
import { loadMonitorConfig, validateConfig } from './config.mjs';
import { WebhookMonitor } from './monitor.mjs';
import { TelegramNotifier } from './telegram.mjs';
import { FirestoreAttemptStore } from './storage-firestore.mjs';
import { MemoryAttemptStore } from './storage-memory.mjs';
import { createWebhookHandler } from './http-adapter.mjs';

const config = loadMonitorConfig();
const errors = validateConfig(config);
if (errors.length > 0) {
  console.error(errors.join('\n'));
  process.exit(1);
}

const store = process.env.WEBHOOK_STORE === 'memory'
  ? new MemoryAttemptStore()
  : new FirestoreAttemptStore({ collectionPrefix: process.env.WEBHOOK_COLLECTION_PREFIX || 'webhook_monitor' });

const notifier = new TelegramNotifier({
  botToken: config.telegramBotToken,
  chatId: config.telegramChatId
});

const monitor = new WebhookMonitor({ store, notifier, config });

const routes = {
  '/webhooks/anymarket/transmission-update': createWebhookHandler({
    monitor,
    routeConfig: {
      projectId: process.env.PROJECT_ID || 'allpost',
      provider: 'anymarket',
      webhookName: 'transmission_update'
    }
  }),
  '/webhooks/shopee/quotation': createWebhookHandler({
    monitor,
    routeConfig: {
      projectId: process.env.PROJECT_ID || 'allpost',
      provider: 'shopee',
      webhookName: 'quotation'
    }
  })
};

const server = createServer(async (request, response) => {
  if (request.method === 'GET' && request.url === '/health') {
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ ok: true, service: config.serviceName }));
    return;
  }

  const path = request.url?.split('?')[0];
  const handler = routes[path];

  if (!handler) {
    response.writeHead(404, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ ok: false, error: 'route_not_found' }));
    return;
  }

  try {
    await handler(request, response);
  } catch (error) {
    console.error('webhook_handler_error', error);
    response.writeHead(500, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ ok: false, error: 'internal_error' }));
  }
});

const port = Number(process.env.PORT || 8080);
server.listen(port, () => {
  console.log(`Webhook monitor listening on ${port}`);
});
