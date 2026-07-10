# Daily Brief - Release 0.9

Status: implementado v1 deterministico

## Proposito

O Daily Brief consolida a visao operacional do dia em uma unica saida local ou Cloud Shell.

Ele reune agenda, proximo compromisso, janelas livres, conflitos, emails criticos, prioridades, follow-ups, ActionPlans, subscriptions, seguranca e auditoria.

## Arquitetura

```text
ContextRepository
 -> ContextEngine
 -> ContextSnapshot
 -> DailyBriefBuilder
 -> DailyBrief
 -> Text/JSON Renderer
```

O builder nao acessa Gmail, Outlook, Google Calendar, Firestore ou internet diretamente.

## DailyAgenda vs DailyBrief

`DailyAgenda` e centrada em calendario e compromissos.

`DailyBrief` e a visao operacional consolidada do dia. Ele pode usar os campos de agenda ja presentes no `ContextSnapshot`, mas nao recria o pipeline de calendario.

## Status

`ERROR`:

- auditoria `ERROR` com discrepancia critica aberta.

`WARNING`:

- emails criticos;
- conflito de agenda;
- risco alto;
- follow-up;
- alerta de seguranca;
- auditoria `WARNING`.

`OK`:

- nenhuma condicao de erro ou alerta relevante.

## Persistencia

```text
daily_briefs/{date}:{scope}
```

O upsert e idempotente por data e escopo de contas. `daily_agendas` nao e alterada.

## Uso

```bash
python scripts/daily_brief.py --project-id agenda-pessoal-projeto --dry-run
python scripts/daily_brief.py --project-id agenda-pessoal-projeto --json --no-persist
make daily-brief
make daily-brief-json
```

## Seguranca

O Daily Brief:

- nao usa IA;
- nao acessa links;
- nao abre anexos;
- nao envia emails ou WhatsApp;
- nao executa ActionPlans;
- nao modifica providers;
- nao exibe tokens, secrets, corpos completos ou URLs completas.

## Futuro

Email, WhatsApp, push notification e Dashboard poderao consumir o mesmo modelo `DailyBrief` em releases posteriores.
