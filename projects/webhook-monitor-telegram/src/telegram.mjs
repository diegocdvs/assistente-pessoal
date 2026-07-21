export function escapeTelegramText(value) {
  return String(value ?? '').replace(/[<>]/g, '');
}

export function formatTelegramAlert(incident) {
  return [
    '🚨 Alerta de Webhook',
    '',
    `Projeto: ${escapeTelegramText(incident.projectId)}`,
    `Webhook: ${escapeTelegramText(incident.provider)} / ${escapeTelegramText(incident.webhookName)}`,
    `Evento: ${escapeTelegramText(incident.eventKey)}`,
    `Tentativas: ${incident.attemptCount}`,
    `Regra: ${escapeTelegramText(incident.ruleTriggered)}`,
    `Primeira tentativa: ${escapeTelegramText(incident.firstAttemptAt)}`,
    `Última tentativa: ${escapeTelegramText(incident.lastAttemptAt)}`,
    '',
    'Ação sugerida: verificar retry do provedor, resposta HTTP do endpoint e processamento interno.'
  ].join('\n');
}

export class TelegramNotifier {
  constructor({ botToken, chatId, fetchImpl = globalThis.fetch } = {}) {
    this.botToken = botToken;
    this.chatId = chatId;
    this.fetchImpl = fetchImpl;
  }

  isConfigured() {
    return Boolean(this.botToken && this.chatId);
  }

  async sendIncident(incident) {
    if (!this.isConfigured()) {
      return { ok: false, skipped: true, reason: 'Telegram bot token or chat id is missing.' };
    }

    const response = await this.fetchImpl(`https://api.telegram.org/bot${this.botToken}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        chat_id: this.chatId,
        text: formatTelegramAlert(incident),
        disable_web_page_preview: true
      })
    });

    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      return {
        ok: false,
        status: response.status,
        error: body.description || 'Telegram API returned an error.'
      };
    }

    return { ok: true, telegramMessageId: body.result?.message_id };
  }
}
