# ADR-014 - Daily Brief deterministico como consumidor de contexto

Status: aceito  
Data: 2026-07-10

## Contexto

O assistente precisa entregar uma visao diaria util sem executar acoes e sem depender de IA generativa.

## Decisao

Criar `DailyBrief` como modelo consolidado e deterministico gerado a partir de `ContextSnapshot`.

Fluxo:

```text
ContextRepository -> ContextEngine -> ContextSnapshot -> DailyBriefBuilder -> DailyBrief
```

## Motivos

- Determinismo torna o resultado testavel e auditavel.
- IA nao e necessaria para a primeira versao de uso diario.
- `ContextSnapshot` ja e o contrato para consumidores futuros.
- O brief nao deve acessar providers nem Firestore diretamente no builder.
- `DailyAgenda` permanece centrada em calendario; `DailyBrief` consolida a operacao do dia.
- Envio por email, WhatsApp ou outro canal exige politica propria e fica para release posterior.

## Consequencias

- CLI, canais futuros e dashboards podem consumir o mesmo modelo.
- O brief pode ser persistido de forma idempotente em `daily_briefs`.
- Nenhuma acao mutavel e executada nesta release.
