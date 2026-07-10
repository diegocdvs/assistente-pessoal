# Communication Manager

Status: fundacao implementada na Release 0.7

## Objetivo

Consolidar capacidades de comunicacao pessoal em uma camada unica, sem acoplar o dominio a Gmail, Outlook ou futuros providers.

## Modulos previstos

1. Subscription Manager.
2. Follow-up Manager.
3. Contact/Relationship Context.
4. Notification Manager.
5. Communication Audit.

## Subscription Manager - Release 0.7

Fluxo implementado:

```text
EmailEntity
 -> SubscriptionDetector
 -> RFC Parser
 -> SubscriptionAggregator
 -> SubscriptionRepository
 -> RecommendationEngine
 -> ActionPlan waiting_approval
```

Nao ha executor de unsubscribe.

### Entrada

Usa apenas dados normalizados de e-mail e headers disponiveis. Nao faz scraping e nao abre links.

### Deteccao

Priorizar sinais padronizados:

- `List-Unsubscribe`;
- `List-Unsubscribe-Post`;
- `List-ID`;
- `List-Post`;
- `Precedence`;
- `Auto-Submitted`;
- recorrencia de remetente como sinal complementar.

### Entidade

`SubscriptionEntity` deve conter:

- subscription_id;
- account_id;
- provider;
- sender;
- sender_domain;
- display_name;
- category;
- first_seen_at;
- last_received_at;
- message_count;
- estimated_frequency;
- unsubscribe_supported;
- unsubscribe_methods;
- unsubscribe_url;
- unsubscribe_email;
- one_click_supported;
- status;
- recommendation_score;
- recommendation_reasons;
- latest_security_risk_level;
- latest_security_risk_score;
- audit_metadata;
- schema_version.

### Estados

- detected;
- active;
- ignored;
- favorite;
- unsubscribe_recommended;
- waiting_approval;
- approved;
- unsubscribed;
- failed;
- quarantined.

## Fluxo seguro de unsubscribe

```text
Detectar subscription
 -> validar headers e origem
 -> Threat Analyzer
 -> gerar ActionPlan unsubscribe_subscription
 -> autorizacao explicita do usuario
 -> Executor isolado
 -> registrar resultado e auditoria
```

Nunca:

- clicar automaticamente;
- abrir navegador;
- seguir redirects;
- executar JavaScript;
- fazer scraping;
- enviar `mailto` sem autorizacao;
- considerar unsubscribe concluido sem evidencia.

## Etapas de implementacao

### Fase 1 - Fundacao

- Security Layer e Threat Analyzer minimo.
- modelos e contratos;
- repository;
- parser RFC;
- deteccao read-only;
- testes com headers reais anonimizados.

### Fase 2 - Visibilidade

- listar e filtrar subscriptions;
- recomendacoes deterministicas;
- integrar ao `ContextSnapshot`;
- relatorio de volume e recorrencia.

### Fase 3 - Planejamento

- gerar `ActionPlan` de unsubscribe;
- policy de aprovacao;
- auditoria e idempotencia;
- nenhuma execucao real ainda.

### Fase 4 - Execucao controlada

- executar apenas mecanismo oficial RFC;
- validar URL/protocolo/dominio;
- bloquear risco alto;
- registrar resposta, falha e retry limitado;
- feature flag desligada por padrao.

## Criterios para iniciar

- `SECURITY.md` e `THREAT_MODEL.md` aprovados;
- Security Layer disponivel;
- ActionPlan auditavel;
- politica de autorizacao definida;
- testes e rollback definidos;
- Double Check planejado para validar consistencia.

## Fora de escopo inicial

- scraping de paginas;
- unsubscribe em massa sem revisao;
- abertura de anexos;
- IA para clicar ou navegar;
- alteracao de mensagens na origem.

## Parser RFC

O parser em `app/communication/rfc_parser.py` interpreta:

- multiplos valores em `List-Unsubscribe`;
- URLs HTTP/HTTPS;
- `mailto`;
- `List-Unsubscribe-Post: List-Unsubscribe=One-Click`;
- casing e espacos variados;
- valores malformados;
- mecanismos duplicados.

Ele nunca faz requisicoes, nunca valida disponibilidade externa e nunca segue redirects.

## Aggregation

`SubscriptionAggregator` consolida de forma deterministica e idempotente:

1. `account_id + provider + List-ID`;
2. `account_id + provider + sender_domain + unsubscribe target`;
3. `account_id + provider + sender`.

## Repository

Contratos implementados:

- `InMemorySubscriptionRepository`;
- `FirestoreSubscriptionRepository`.

Persistencia:

```text
accounts/{account_id}/subscriptions/{subscription_id}
```

## Recommendation Engine

O algoritmo e deterministico e considera categoria, volume, frequencia, mecanismo RFC e risco de seguranca.

Regras atuais:

- `favorite` nao e recomendada automaticamente;
- `ignored` nao reaparece repetidamente;
- ausencia de mecanismo RFC impede ActionPlan;
- risco `high` ou `critical` bloqueia execucao e exige revisao manual;
- recomendacao nao e aprovacao.

## Approval

`SubscriptionApproval` existe como contrato com status:

```text
pending, approved, rejected, expired, revoked
```

Nesta release, aprovacao nao aciona executor porque executor real nao existe.

## Daily Brief

O Daily Brief consome subscriptions recomendadas e aguardando aprovacao via `ContextSnapshot`. Ele nao executa unsubscribe e nao altera status de subscriptions.
