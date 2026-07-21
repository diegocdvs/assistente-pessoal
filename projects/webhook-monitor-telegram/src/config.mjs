export function loadMonitorConfig(env = process.env) {
  return {
    mode: env.WEBHOOK_MONITOR_MODE || 'retry_sequence',
    attemptThreshold: Number(env.WEBHOOK_ATTEMPT_THRESHOLD || 5),
    minGapSeconds: Number(env.WEBHOOK_MIN_GAP_SECONDS || 45),
    maxGapSeconds: Number(env.WEBHOOK_MAX_GAP_SECONDS || 75),
    lookbackMinutes: Number(env.WEBHOOK_LOOKBACK_MINUTES || 10),
    cooldownMinutes: Number(env.WEBHOOK_COOLDOWN_MINUTES || 30),
    telegramBotToken: env.TELEGRAM_BOT_TOKEN || '',
    telegramChatId: env.TELEGRAM_CHAT_ID || '',
    serviceName: env.K_SERVICE || env.SERVICE_NAME || 'webhook-monitor'
  };
}

export function validateConfig(config) {
  const errors = [];

  if (!Number.isFinite(config.attemptThreshold) || config.attemptThreshold < 1) {
    errors.push('WEBHOOK_ATTEMPT_THRESHOLD must be a positive number.');
  }

  if (!Number.isFinite(config.minGapSeconds) || config.minGapSeconds < 0) {
    errors.push('WEBHOOK_MIN_GAP_SECONDS must be zero or positive.');
  }

  if (!Number.isFinite(config.maxGapSeconds) || config.maxGapSeconds < config.minGapSeconds) {
    errors.push('WEBHOOK_MAX_GAP_SECONDS must be greater than or equal to WEBHOOK_MIN_GAP_SECONDS.');
  }

  if (!Number.isFinite(config.cooldownMinutes) || config.cooldownMinutes < 0) {
    errors.push('WEBHOOK_COOLDOWN_MINUTES must be zero or positive.');
  }

  if (!['retry_sequence', 'burst_window'].includes(config.mode)) {
    errors.push('WEBHOOK_MONITOR_MODE must be retry_sequence or burst_window.');
  }

  return errors;
}
