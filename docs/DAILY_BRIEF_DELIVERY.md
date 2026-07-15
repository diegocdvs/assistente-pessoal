# Daily Brief Delivery - Release 0.10

Status: implementado, desligado por padrao

## Proposito

A Release 0.10 entrega o `DailyBrief` existente por Gmail de forma segura, auditavel e idempotente.

Fluxo:

```text
DailyBrief
 -> Delivery Policy
 -> Email Renderer
 -> Draft or Send
 -> Delivery Audit
```

O builder do Daily Brief nao muda. Ele continua consumindo apenas `ContextSnapshot`.

## Defaults seguros

```bash
DAILY_BRIEF_DELIVERY_ENABLED=false
DAILY_BRIEF_DELIVERY_MODE=disabled
DAILY_BRIEF_DELIVERY_ALLOW_SEND=false
```

Modos:

- `disabled`: nao cria rascunho e nao envia.
- `draft`: cria apenas rascunho no Gmail, quando a policy permitir.
- `send`: envia e-mail apenas com `DAILY_BRIEF_DELIVERY_ALLOW_SEND=true`.

`send` nunca e ativado por padrao.

## Configuracao

```bash
DAILY_BRIEF_DELIVERY_ENABLED=true
DAILY_BRIEF_DELIVERY_MODE=draft
DAILY_BRIEF_DELIVERY_RECIPIENTS=destinatario@example.com
DAILY_BRIEF_DELIVERY_SENDER_ACCOUNT_ID=pessoal_google
DAILY_BRIEF_DELIVERY_SECRET_PREFIX=google-pessoal
DAILY_BRIEF_DELIVERY_TIMEZONE=America/Sao_Paulo
DAILY_BRIEF_DELIVERY_START_HOUR=5
DAILY_BRIEF_DELIVERY_END_HOUR=11
```

Para envio real:

```bash
DAILY_BRIEF_DELIVERY_MODE=send
DAILY_BRIEF_DELIVERY_ALLOW_SEND=true
```

Destinatarios devem estar na allowlist `DAILY_BRIEF_DELIVERY_RECIPIENTS`. Wildcard nao e aceito.

## Policy

Decisoes possiveis:

- `ALLOW_DRAFT`
- `ALLOW_SEND`
- `BLOCK`
- `REVIEW`

A policy bloqueia ou exige revisao quando:

- delivery esta desabilitado;
- destinatario nao esta na allowlist;
- janela de entrega esta fora do horario configurado;
- o brief esta em `ERROR`;
- existem discrepancias abertas;
- existem itens de alto risco e o modo e `send`;
- `send` foi solicitado sem `DAILY_BRIEF_DELIVERY_ALLOW_SEND=true`.

## Idempotencia

A chave de idempotencia usa:

```text
brief_id + account_id + recipient + mode
```

Se a entrega ja existir, o service registra `skipped` e nao chama Gmail. Use `--force` apenas em operacao manual controlada.

## Persistencia

Auditoria:

```text
daily_brief_deliveries/{delivery_id}
```

O registro contem:

```text
delivery_id, brief_id, account_id, recipient, mode, policy_decision,
policy_reason, status, idempotency_key, gmail_draft_id,
gmail_message_id, error, created_at, updated_at, metadata, schema_version
```

O corpo do e-mail nao e persistido.

## CLI

```bash
python scripts/daily_brief_delivery.py --project-id agenda-pessoal-projeto --use-last-brief --json
python scripts/daily_brief_delivery.py --project-id agenda-pessoal-projeto --mode draft --use-last-brief
python scripts/daily_brief_delivery.py --project-id agenda-pessoal-projeto --mode send --use-last-brief
```

Dry-run explicito:

```bash
python scripts/daily_brief_delivery.py --project-id agenda-pessoal-projeto --mode draft --dry-run --use-last-brief
```

## Make

```bash
make daily-brief-draft
make daily-brief-deliver
```

`daily-brief-draft` forca modo `draft`. `daily-brief-deliver` respeita as variaveis de ambiente.

## Agendamento

O agendamento diario nao fica nesta camada. A Release 0.11 adiciona `app/scheduled_daily_brief`, que chama a delivery somente depois de adquirir uma idempotency key propria da rotina diaria.

Consulte:

```text
docs/SCHEDULED_DAILY_BRIEF.md
docs/setup/SCHEDULED_DAILY_BRIEF_GCP_SETUP.md
```

## Garantias

- nao altera GmailConnector;
- nao le inbox;
- nao marca e-mail como lido;
- nao move, arquiva ou exclui mensagens;
- nao cria evento;
- nao envia WhatsApp;
- nao envia para destinatario fora da allowlist;
- nao executa envio real sem `DAILY_BRIEF_DELIVERY_ALLOW_SEND=true`.
