# Webhook Monitor Telegram

Módulo genérico para monitorar tentativas de webhooks e enviar alerta no Telegram quando houver 5 tentativas consecutivas para o mesmo webhook/evento, com intervalo aproximado de 1 minuto entre elas.

## Regra padrão

- Modo: `retry_sequence`
- Limiar: 5 tentativas
- Gap aceito: 45 a 75 segundos entre tentativas
- Cooldown: 30 minutos por chave de webhook/evento

## Chave de agrupamento

```txt
project_id + provider + webhook_name + event_key
```

Exemplo:

```txt
allpost:anymarket:transmission_update:content_id_100605943
```

## Instalação local

```bash
npm install
npm test
npm run smoke
```

## Rodando localmente com storage em memória

```bash
cp .env.example .env
WEBHOOK_STORE=memory npm start
```

Health check:

```bash
curl http://localhost:8080/health
```

Teste de webhook:

```bash
curl -X POST http://localhost:8080/webhooks/anymarket/transmission-update \
  -H 'content-type: application/json' \
  -d '{"content":{"id":"100605943"}}'
```

## Deploy sugerido

- Cloud Run para execução.
- Firestore para armazenar tentativas, incidentes e cooldown.
- Secret Manager para `TELEGRAM_BOT_TOKEN`.
- Variável protegida para `TELEGRAM_CHAT_ID`.

## Segurança

- Não envia payload completo no Telegram.
- Armazena hash do payload para correlação.
- Evita dados pessoais em alertas.
- Usa cooldown para evitar spam.
