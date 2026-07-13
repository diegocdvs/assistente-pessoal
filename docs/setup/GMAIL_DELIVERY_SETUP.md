# Gmail Delivery Setup

Status: opcional, usado apenas para Daily Brief Delivery

## Escopos

Para criar rascunhos:

```text
https://www.googleapis.com/auth/gmail.compose
```

Para enviar e-mails:

```text
https://www.googleapis.com/auth/gmail.send
```

`gmail.compose` permite criar rascunhos e tambem enviar e-mail pela API Gmail. Para menor privilegio operacional, a Release 0.10 solicita:

- `gmail.compose` quando o objetivo for rascunho;
- `gmail.send` quando o objetivo for envio.

## Gerar refresh token

Rascunho:

```bash
python scripts/google_oauth_local.py --client-secret-file client_secret.json --include-gmail-draft
```

Envio:

```bash
python scripts/google_oauth_local.py --client-secret-file client_secret.json --include-gmail-send
```

Rascunho e envio:

```bash
python scripts/google_oauth_local.py --client-secret-file client_secret.json --include-gmail-draft --include-gmail-send
```

O helper grava os secrets no Secret Manager se o operador confirmar:

```text
<secret_prefix>-client-secret-json
<secret_prefix>-refresh-token
```

## Variaveis de ambiente

```bash
DAILY_BRIEF_DELIVERY_ENABLED=true
DAILY_BRIEF_DELIVERY_MODE=draft
DAILY_BRIEF_DELIVERY_RECIPIENTS=destinatario@example.com
DAILY_BRIEF_DELIVERY_SECRET_PREFIX=google-pessoal
DAILY_BRIEF_DELIVERY_SENDER_ACCOUNT_ID=pessoal_google
```

Para envio real:

```bash
DAILY_BRIEF_DELIVERY_MODE=send
DAILY_BRIEF_DELIVERY_ALLOW_SEND=true
```

## Validacao segura

```bash
python scripts/daily_brief_delivery.py --project-id agenda-pessoal-projeto --mode draft --dry-run --use-last-brief --json
make daily-brief-draft
```

Se o modo estiver `disabled`, a execucao registra `skipped` e nao chama Gmail.

## Limites

A Release 0.10 nao implementa:

- anexos;
- CC/BCC;
- reply/threading;
- tracking;
- template remoto;
- scheduler;
- WhatsApp;
- Outlook delivery.
