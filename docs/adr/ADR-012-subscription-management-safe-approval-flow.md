# ADR-012 - Subscription Management com fluxo seguro de aprovacao

Status: aceito  
Data: 2026-07-10

## Contexto

Newsletters, listas de distribuicao e comunicacoes recorrentes precisam ser acompanhadas como estado operacional agregado. Uma mensagem individual pode indicar uma subscription, mas a decisao de recomendar cancelamento depende de historico, frequencia, risco e mecanismo oficial disponivel.

## Decisao

Criar `SubscriptionEntity` como entidade separada de `WorkItem`.

O fluxo da Release 0.7 e:

```text
EmailEntity
 -> SubscriptionDetector
 -> RFC Parser
 -> SubscriptionAggregator
 -> SubscriptionRepository
 -> RecommendationEngine
 -> ActionPlan unsubscribe_subscription
```

Deteccao e separada da execucao. A release nao inclui executor.

## Motivos

- `WorkItem` representa um item processavel individual; `SubscriptionEntity` representa estado agregado e historico recorrente.
- Headers RFC, como `List-Unsubscribe` e `List-ID`, sao mais confiaveis do que assunto promocional ou heuristicas soltas.
- Recomendacao de unsubscribe pode ser util, mas nao equivale a aprovacao.
- Unsubscribe pode ser abusado por phishing, redirects, tracking, `mailto` malicioso ou headers forjados.
- Scraping e navegador aumentariam superficie de ataque e nao sao necessarios para a fundacao.
- Risco `high` ou `critical` deve bloquear qualquer execucao e exigir revisao manual.

## Regras

- Nenhum link e acessado.
- Nenhum redirect e seguido.
- Nenhum `mailto` e enviado.
- Nenhum scraping e realizado.
- Nenhum navegador e aberto.
- Nenhum provider e alterado.
- Todo `ActionPlan` de unsubscribe nasce com `approval_required=true`, `execution_enabled=false` e `dry_run=true`.
- Estados `approved`, `unsubscribed` e `failed` existem como contrato, mas nao sao produzidos automaticamente nesta release.

## Consequencias

- O Communication Manager pode detectar e recomendar de forma auditavel sem executar acoes externas.
- O futuro executor devera ser isolado, idempotente, protegido pela Security Foundation e desligado por padrao.
- Double Check pode auditar inconsistencias sem reprocessar nem corrigir automaticamente.
