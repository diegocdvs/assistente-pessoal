# Deploy em Cloud Run

## 1. Preparar projeto Google Cloud

Ative:

- Cloud Run
- Artifact Registry
- Firestore
- Secret Manager

## 2. Criar secret do Telegram

```bash
gcloud secrets create telegram-bot-token --replication-policy="automatic"
printf "TOKEN_DO_BOT" | gcloud secrets versions add telegram-bot-token --data-file=-
```

## 3. Build e deploy

```bash
gcloud run deploy webhook-monitor \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=allpost,WEBHOOK_STORE=firestore,WEBHOOK_MONITOR_MODE=retry_sequence,WEBHOOK_ATTEMPT_THRESHOLD=5,WEBHOOK_MIN_GAP_SECONDS=45,WEBHOOK_MAX_GAP_SECONDS=75,WEBHOOK_COOLDOWN_MINUTES=30,TELEGRAM_CHAT_ID=SEU_CHAT_ID \
  --set-secrets TELEGRAM_BOT_TOKEN=telegram-bot-token:latest
```

## 4. Rotas iniciais

- `/webhooks/anymarket/transmission-update`
- `/webhooks/shopee/quotation`
- `/health`

## 5. Observação

Antes de produção, restrinja origem/autenticação dos webhooks conforme o provedor permitir.
