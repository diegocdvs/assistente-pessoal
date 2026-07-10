# ADR-013 - Calendar read-only integrado ao contexto

Status: aceito  
Data: 2026-07-10

## Contexto

O assistente precisa entregar valor diario com agenda, conflitos e janelas livres, sem ganhar capacidade de modificar compromissos.

## Decisao

Criar `CalendarEvent` como entidade de dominio separada de `EmailEntity` e implementar `GoogleCalendarConnector` exclusivamente read-only.

O Context Engine consome eventos apenas via repository:

```text
CalendarConnector -> CalendarEvent -> CalendarRepository -> ContextEngine -> DailyAgenda
```

## Motivos

- Eventos de agenda possuem semantica propria e nao devem ser forçados para `EmailEntity`.
- Connector nao implementa regra de negocio.
- Context Engine nao acessa Google Calendar nem qualquer API externa.
- Daily Agenda e deterministica e testavel sem IA.
- Microsoft Calendar fica para release posterior para evitar misturar providers e OAuths.
- O modelo suporta Google Calendar, Microsoft Calendar, CalDAV e outros providers por contrato comum.

## Regras

- Usar apenas escopos read-only.
- Nao criar, atualizar, excluir, mover ou responder eventos.
- Nao acessar meeting URLs, links ou anexos.
- Nao expor descricoes completas, tokens ou meeting URLs em logs.
- Acoes mutaveis de Calendar exigem release futura com aprovacao, idempotencia, auditoria e feature flag desligada.
