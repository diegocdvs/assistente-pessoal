# Communication Manager

Status: planejado

## Objetivo

Consolidar capacidades de comunicacao pessoal em uma camada unica, sem acoplar o dominio a Gmail, Outlook ou futuros providers.

## Modulos previstos

1. Subscription Manager.
2. Follow-up Manager.
3. Contact/Relationship Context.
4. Notification Manager.
5. Communication Audit.

## Subscription Manager

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

### Entidade alvo

`SubscriptionEntity` deve conter:

- id;
- account_id;
- provider;
- sender;
- sender_domain;
- display_name;
- category;
- first_seen_at;
- last_received_at;
- message_count;
- frequency_estimate;
- unsubscribe_supported;
- unsubscribe_method;
- unsubscribe_url ou unsubscribe_email;
- status;
- risk_score;
- audit_metadata;
- schema_version.

### Estados

- detected;
- active;
- ignored;
- favorite;
- unsubscribe_proposed;
- unsubscribe_approved;
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
