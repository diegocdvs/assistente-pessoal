# Calendar Architecture - Release 0.8

Status: implementado read-only

## Objetivo

Ler Google Calendar, normalizar compromissos, persistir eventos e alimentar o Context Engine e a Daily Agenda sem conceder capacidade de escrita.

## Fluxo

```text
Google Calendar
 -> CalendarConnector
 -> CalendarEvent
 -> CalendarRepository
 -> Context Engine
 -> Daily Agenda
```

`CalendarEvent` nao e convertido em `EmailEntity`. Quando necessario, ele vira `WorkItem(type="calendar_event")`.

## Escopos OAuth

Escopos read-only usados:

```text
https://www.googleapis.com/auth/calendar.events.readonly
https://www.googleapis.com/auth/calendar.calendarlist.readonly
```

Mudanca de escopo pode exigir nova autorizacao OAuth e novo refresh token.

## Garantias

- Nenhum evento e criado, atualizado, movido ou excluido.
- Nenhum convite e respondido.
- Nenhuma meeting URL e acessada.
- Nenhum link de descricao e acessado.
- Nenhum anexo e aberto.
- Context Engine consome somente dados persistidos.

## Persistencia

```text
accounts/{account_id}/calendar_events/{event_id}
daily_agendas/{date}
```

Eventos usam upsert idempotente, preservam `first_seen_at` quando aplicavel e atualizam `last_seen_at`.

## Daily Agenda

`DailyAgendaBuilder` gera resumo deterministico com compromissos, proximo evento, conflitos, janelas livres, emails criticos, follow-ups, ActionPlans pendentes, subscriptions aguardando aprovacao e alertas de seguranca.

Nao ha IA, LLM, embeddings ou texto generativo.

## Relacao com Daily Brief

`DailyAgenda` e centrada em calendario. `DailyBrief` consolida agenda, emails, prioridades, follow-ups, subscriptions, seguranca e auditoria a partir do `ContextSnapshot`.
