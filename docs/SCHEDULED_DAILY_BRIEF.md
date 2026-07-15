# Scheduled Daily Brief - Release 0.11

Status: implementado, desligado por padrao

## Proposito

Transformar o Daily Brief em uma rotina diaria operacional, segura, idempotente e auditavel.

Fluxo:

```text
Cloud Scheduler
 -> Cloud Run Job
 -> scripts/scheduled_daily_brief.py
 -> ScheduledDailyBriefService
 -> ContextSnapshot
 -> DailyBrief
 -> Delivery Policy
 -> Draft or Send
 -> Scheduled Run Audit
```

O Scheduler nao contem regra de negocio. Ele apenas invoca o Cloud Run Job autenticado.

## Defaults seguros

```bash
DAILY_BRIEF_SCHEDULE_ENABLED=false
DAILY_BRIEF_SCHEDULE_TIME=07:30
DAILY_BRIEF_SCHEDULE_TIMEZONE=America/Sao_Paulo
DAILY_BRIEF_SCHEDULE_MODE=draft
DAILY_BRIEF_SCHEDULE_ACCOUNT_SCOPE=all
DAILY_BRIEF_SCHEDULE_RECIPIENTS=
DAILY_BRIEF_SCHEDULE_MAX_ATTEMPTS=3
DAILY_BRIEF_SCHEDULE_RETRY_DELAY_SECONDS=60
DAILY_BRIEF_SCHEDULE_LOOKBACK_HOURS=24
```

`send` continua dependendo tambem das flags de delivery:

```bash
DAILY_BRIEF_DELIVERY_ALLOW_SEND=true
DAILY_BRIEF_DELIVERY_RECIPIENTS=destinatario@example.com
```

## Idempotencia

A chave considera:

```text
schedule_date
timezone
account_scope
channel=email
delivery_mode
recipient normalizado
schema_version
```

`draft` e `send` possuem identidades distintas.

Uma entrega confirmada (`draft_created` ou `delivered`) sempre resulta em `skipped` em retries posteriores, inclusive com `--force`.

`--force` ignora apenas a janela de horario. Ele nao ignora idempotencia confirmada.

## Falhas e retry

Retryable:

- `timeout`
- `temporary_unavailable`
- `rate_limit`
- `http_5xx`
- `firestore_before_confirmed_delivery`

Non-retryable:

- `missing_credentials`
- `insufficient_oauth_scope`
- `recipient_outside_allowlist`
- `invalid_configuration`
- `blocked_by_policy`
- `security_error`
- `invalid_content`
- `delivery_already_confirmed`
- `delivery_uncertain`

Se houver incerteza apos possivel chamada de entrega, o erro `delivery_uncertain` exige revisao operacional e nao e reenviado automaticamente.

## Auditoria

Colecao:

```text
scheduled_daily_brief_runs/{idempotency_key}
```

Modelo:

```text
run_id, schedule_date, timezone, account_scope, delivery_mode,
recipient_hash, idempotency_key, status, started_at, finished_at,
duration_seconds, brief_id, delivery_id, attempt, trigger, error_code,
error_summary, stage_counts, audit_metadata, schema_version
```

Nao persistir:

- corpo do e-mail;
- HTML completo;
- tokens;
- secrets;
- destinatario completo.

## CLI

```bash
python scripts/scheduled_daily_brief.py --help
python scripts/scheduled_daily_brief.py --trigger test --dry-run --json
python scripts/scheduled_daily_brief.py --show-last-run
python scripts/scheduled_daily_brief.py --list-recent
```

Exit codes:

- `0`: sucesso, skip seguro, draft criado ou delivery confirmado;
- `1`: falha operacional;
- `2`: bloqueio por policy/configuracao.

## Make

```bash
make scheduled-daily-brief
make scheduled-daily-brief-dry-run
make scheduled-daily-brief-status
```

`make release` nao executa o agendamento.

## Double Check

```bash
python scripts/double_check.py --scheduled-daily-brief --json
```

Audita:

- duplicidade de idempotency key;
- entrega confirmada sem audit de delivery;
- running antigo;
- delivery uncertain;
- scheduler ativo com flag desligada;
- send sem allowlist;
- schema_version ausente.
