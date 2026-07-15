# ADR-016 - Scheduled Daily Brief como Job idempotente

## Status

Aceita

## Contexto

O Daily Brief ja pode ser gerado, renderizado, entregue por Gmail em draft/send e auditado. A proxima necessidade de produto e receber esse brief automaticamente todos os dias sem criar duplicidade em retries.

## Decisao

Criar `ScheduledDailyBriefService` e `scripts/scheduled_daily_brief.py` como entrypoint operacional.

O Cloud Scheduler invoca um Cloud Run Job autenticado, usando o mesmo container. O Scheduler nao conhece regras de negocio; ele apenas dispara a execucao.

## Motivos

- Reutilizar o container atual evita nova superficie HTTP publica.
- Iniciar em `draft` permite validar conteudo e fluxo sem envio real.
- Idempotencia e obrigatoria porque Cloud Scheduler, Cloud Run e operadores podem repetir a mesma execucao.
- Entrega incerta (`delivery_uncertain`) nao pode ser reenviada automaticamente porque o Gmail pode ter recebido a requisicao antes da perda de resposta.
- O envio continua isolado do `GmailConnector` para preservar separacao entre leitura e mutacao.
- IA nao e necessaria: o Daily Brief segue deterministico a partir de `ContextSnapshot`.

## Consequencias

- Nova colecao `scheduled_daily_brief_runs/{idempotency_key}`.
- `--force` nao ignora entrega confirmada.
- `send` permanece opt-in com allowlist e `DAILY_BRIEF_DELIVERY_ALLOW_SEND=true`.
- Corpo/HTML do brief nao sao persistidos na auditoria agendada.

## Alternativas descartadas

- Cron local permanente.
- Servico HTTP publico.
- Envio direto no Scheduler.
- Reusar `GmailConnector` para envio.
- Reenviar automaticamente em estado incerto.
