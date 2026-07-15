# Arquitetura Mestre do Assistente Pessoal

Status: documento vivo
Responsável técnico: arquitetura do projeto
Última revisão: após Sprint 1 funcional

## 1. Objetivo do sistema

O Assistente Pessoal deve ser um motor operacional hospedado no Google Cloud capaz de ler eventos de múltiplas fontes, normalizar esses dados em um domínio interno, classificar relevância, persistir histórico, planejar ações e gerar relatórios.

O projeto não deve evoluir como um conjunto de scripts isolados. A direção arquitetural é construir uma plataforma modular de automação pessoal.

## 2. Princípios arquiteturais

1. Conectores não podem vazar detalhes de APIs externas para o núcleo.
2. O núcleo trabalha com modelos internos: `EmailEntity`, `WorkItem`, `Classification`, `ActionPlan` e `Report`.
3. A IA nunca deve conversar diretamente com Gmail, Outlook, Calendar, WhatsApp ou qualquer API externa.
4. Toda ação externa deve passar por `AutomationPlanner` e, futuramente, por `AutomationExecutor`.
5. `DRY_RUN=true` deve impedir qualquer ação mutável.
6. Toda execução deve ser idempotente sempre que possível.
7. Toda mensagem, classificação, plano de ação e execução deve ser rastreável.
8. Adicionar uma nova conta deve exigir configuração, não alteração estrutural de código.
9. Adicionar um novo provedor deve exigir um novo conector, não alteração do pipeline principal.
10. O projeto deve priorizar simplicidade operacional, mas sem criar dívida estrutural desnecessária.

## 3. Arquitetura-alvo

```text
Scheduler / Manual Trigger
        |
        v
AccountManager
        |
        v
ConnectorManager
        |
        +--> GmailConnector
        +--> OutlookConnector
        +--> CalendarConnector
        +--> WhatsAppConnector
        +--> DriveConnector
        |
        v
Domain Entity
        |
        +--> EmailEntity
        +--> CalendarEventEntity
        +--> MessageEntity
        +--> DocumentEntity
        |
        v
WorkItem
        |
        v
Classifier
        |
        v
Persistence
        |
        v
AutomationPlanner
        |
        v
Report
        |
        v
ContextEngine
        |
        v
ContextSnapshot
        |
        v
Security Capability
        |
        v
Future: Notification / WhatsApp / Dashboard
```

## 4. Pipeline obrigatório

O pipeline principal deve seguir esta ordem:

```text
Connector
↓
Domain Entity
↓
WorkItem
↓
Classifier
↓
Persistence
↓
AutomationPlanner
↓
Report
```

A ordem é importante. A persistência deve registrar o estado processado antes de qualquer execução externa futura. A automação deve planejar primeiro e executar depois, separadamente.

## 5. Modelos de domínio

### 5.1 EmailEntity

Representa um e-mail normalizado, independente do provedor.

Campos mínimos:

```text
id
provider
account_id
account_email
thread_id
subject
sender
recipients
snippet
labels
received_at
raw_headers
metadata
```

O Gmail pode ter `labelIds`; o Outlook pode ter `categories`; ambos devem ser normalizados antes de entrar no núcleo.

### 5.2 WorkItem

Modelo genérico para qualquer item processável pelo assistente.

```text
id
source
type
account_id
payload
created_at
schema_version
```

Exemplos:

```text
source=gmail, type=email, payload=EmailEntity
source=calendar, type=event, payload=CalendarEventEntity
source=whatsapp, type=message, payload=MessageEntity
source=drive, type=document, payload=DocumentEntity
```

A camada de IA deve operar preferencialmente sobre `WorkItem`, não sobre APIs específicas.

Na Release 0.2, `EmailEntity` ja pode ser convertido para `WorkItem`. O pipeline Gmail continua recebendo `EmailEntity` do conector, mas cria um `WorkItem` conceitual no core para preparar Calendar, WhatsApp, IA e automacoes futuras sem alterar o `GmailConnector`.

### 5.3 Classification

Campos mínimos:

```text
category
priority
confidence
reason
possible_event
```

Categorias iniciais:

```text
financeiro
compra
entrega
evento
trabalho
seguranca
promocao
newsletter
social
educacao
viagem
saude
sistema
outros
```

Prioridades iniciais:

```text
critica
alta
normal
baixa
ruido
```

### 5.4 ActionPlan

Representa uma ação planejada, não executada.

Campos mínimos:

```text
id
source
type
reason
dry_run
status
payload
created_at
updated_at
audit_metadata
schema_version
```

Estados possíveis:

```text
planned
skipped
waiting_approval
executed
failed
```

Enquanto `DRY_RUN=true`, nenhum plano deve ser executado.

Na Release 0.2, `ActionPlan` segue sem executor real. Os novos campos existem apenas para auditoria, rastreabilidade e compatibilidade futura.

### 5.5 ContextSnapshot

Representa o estado operacional atual do usuario.

Campos principais:

```text
date
generated_at
emails_pending
emails_critical
followups
upcoming_commitments
important_people
recent_decisions
action_plans
work_items
top_priorities
summary
source_counts
```

`ContextSnapshot` e o contrato que futuros consumers devem usar para IA, Dashboard, WhatsApp, resumos e Planner.

### 5.6 SecurityAssessment

Representa analise estatica de risco para conteudo externo.

Campos principais:

```text
assessment_id
provider
source_id
risk_score
risk_level
risk_reasons
link_count
attachment_count
external_images
suspicious_headers
spoofing_signals
authentication_signals
created_at
schema_version
```

`SecurityAssessment` e produzido por `ThreatAnalyzer` e nao executa acoes.

### 5.7 SubscriptionEntity

Representa uma comunicacao recorrente agregada, independente de Gmail ou Outlook.

Campos principais:

```text
subscription_id
account_id
provider
sender
sender_domain
display_name
list_id
category
first_seen_at
last_received_at
message_count
estimated_frequency
unsubscribe_supported
unsubscribe_methods
unsubscribe_url
unsubscribe_email
one_click_supported
status
recommendation_score
recommendation_reasons
latest_security_risk_level
latest_security_risk_score
audit_metadata
schema_version
```

Subscriptions sao separadas de `WorkItem` porque representam estado agregado e historico recorrente, nao uma mensagem individual.

### 5.8 CalendarEvent

Representa um compromisso normalizado e independente de provider.

Campos principais:

```text
id, provider, account_id, calendar_id, title, description_summary,
location, start_at, end_at, timezone, all_day, status, organizer,
attendees, attendee_count, user_response_status, recurrence_id,
recurring, meeting_url_present, visibility, source_updated_at,
metadata, created_at, updated_at, schema_version
```

`CalendarEvent` pode virar `WorkItem(type="calendar_event")`, mas nao e `EmailEntity`.

## 6. Conectores

### 6.1 Interface desejada

Todo conector deve seguir a interface comum definida em `app/connectors/base.py`:

```python
class Connector:
    provider: str

    def fetch_recent(self, account) -> list[EmailEntity]:
        ...
```

O conector é responsável por:

- autenticação específica do provedor;
- leitura da API externa;
- tratamento de paginação inicial;
- normalização para entidade de domínio;
- devolver entidade de dominio normalizada, hoje `EmailEntity`.

O conector não deve:

- classificar;
- decidir prioridade;
- persistir no Firestore diretamente;
- executar ações de automação;
- enviar relatório.

Na Release 0.3B, `gmail` e `outlook` compartilham esse contrato. Gmail segue funcional; Outlook possui integracao Microsoft Graph read-only, desabilitada por padrao por `OUTLOOK_ENABLED=false`.

### 6.2 GmailConnector

Responsável por:

- carregar secrets via Secret Manager;
- autenticar com refresh token;
- ler mensagens;
- normalizar para `EmailEntity`;
- preservar metadados relevantes.

Não deve marcar como lido, mover, excluir ou arquivar enquanto não houver um executor específico com aprovação de segurança.

### 6.3 OutlookConnector

Status atual: Microsoft Graph read-only atras de feature flag.

O `OutlookConnector` implementa a mesma interface de conector e depende de abstracoes:

- `OAuthProvider`;
- `OutlookMessageClient`;
- `OutlookNormalizer`.

MSAL fica isolado em `app/auth/microsoft.py`. O cliente HTTP Graph fica em `app/integrations/microsoft_graph.py`.

O fluxo validado por testes e:

```text
Microsoft Graph payload
  -> OutlookNormalizer
  -> EmailEntity
  -> WorkItem
```

A integração Outlook não deve exigir mudanças no `DailyJob` além de registrar o conector no `ConnectorManager`.

Ativacao real exige `OUTLOOK_ENABLED=true` e secrets Microsoft no Secret Manager. Por padrao, Outlook permanece desabilitado.

Detalhes estao em `docs/OUTLOOK_DESIGN.md`.

### 6.4 CalendarConnector futuro

Calendar não deve ser tratado como parte do Gmail. Deve ser um conector próprio.

Funções futuras:

- ler eventos;
- identificar conflitos;
- planejar criação de eventos;
- executar criação apenas via `AutomationExecutor`.

### 6.5 WhatsAppConnector futuro

WhatsApp terá dois papéis distintos:

1. Fonte de mensagens recebidas.
2. Canal de notificação proativa.

Essas duas responsabilidades devem ser separadas.

## 7. AccountManager

O `AccountManager` deve carregar contas de `config/accounts.yaml`.

Adicionar uma conta deve seguir este padrão:

```yaml
accounts:
  - id: pessoal_google
    label: Pessoal
    provider: gmail
    enabled: true
    email: diegocdvs13@gmail.com
    secret_prefix: google-pessoal
    max_emails: 10
```

Secrets derivados:

```text
<secret_prefix>-client-secret-json
<secret_prefix>-refresh-token
```

Exemplo:

```text
google-pessoal-client-secret-json
google-pessoal-refresh-token
```

Secrets Outlook derivados de `secret_prefix`:

```text
<secret_prefix>-tenant-id
<secret_prefix>-client-id
<secret_prefix>-client-secret
<secret_prefix>-token-cache
```

## 7.1 Configuracao centralizada

`app/config.py` centraliza a configuracao operacional basica:

```text
PROJECT_ID
REGION
DRY_RUN
ACCOUNTS_CONFIG_PATH
MAX_EMAILS_PER_PROVIDER
```

Feature flags preparatorias:

```text
OUTLOOK_ENABLED=false
CALENDAR_ENABLED=false
WHATSAPP_ENABLED=false
AI_ENABLED=false
AUTO_EXECUTION_ENABLED=false
```

`OUTLOOK_ENABLED=true` ativa o conector Outlook read-only. As demais flags seguem preparatorias.

## 8. Persistence Layer

Firestore deve ser acessado por uma camada própria, não diretamente pelo pipeline.

Estrutura recomendada:

```text
runs/{run_id}
accounts/{account_id}/emails/{message_id}
accounts/{account_id}/classifications/{message_id}
accounts/{account_id}/action_plans/{message_id}
accounts/{account_id}/subscriptions/{subscription_id}
accounts/{account_id}/calendar_events/{event_id}
daily_agendas/{date}
daily_briefs/{date}:{scope}
daily_brief_deliveries/{delivery_id}
scheduled_daily_brief_runs/{idempotency_key}
```

Campos operacionais importantes:

```text
created_at
processed_at
last_seen_at
run_id
hash
version
schema_version
```

### 8.1 Idempotência

Processar o mesmo e-mail duas vezes não deve duplicar documentos.

Regra:

- `message_id` é a chave primária para e-mails.
- `thread_id` pode ser usado para agrupamento.
- `last_seen_at` deve ser atualizado a cada nova execução.
- `processed_at` registra a primeira ou mais recente classificação, conforme política definida.

## 9. Classifier

A classificação deve evoluir em camadas.

### 9.1 Camada 1 — Regras determinísticas

Regras simples, previsíveis e baratas.

Exemplos:

- recibo, fatura, boleto, pagamento → financeiro ou compra;
- login, senha, código, verificação → segurança;
- promoção, desconto, cupom, oferta, 24h, % OFF → promoção;
- newsletter, tutorial, atualização semanal → newsletter;
- entrevista, reunião, convite, agenda, meet, zoom → evento ou trabalho;
- entrega, rastreio, pedido enviado → entrega.

### 9.2 Camada 2 — Heurísticas contextuais

Resolver falsos positivos:

- promoção com data não é evento;
- tutorial não é evento;
- newsletter com webinar pode ser evento de baixa prioridade;
- oferta de emprego é trabalho, mas só vira prioridade alta se envolver entrevista, prazo, convite direto ou resposta personalizada.

### 9.3 Camada 3 — IA futura

A IA só deve entrar depois das regras básicas.

A IA deve receber:

- WorkItem normalizado;
- classificação preliminar;
- histórico contextual;
- instruções de política.

A IA deve devolver:

- classificação refinada;
- justificativa;
- confidence;
- possíveis ações.

A IA não executa ações.

## 10. AutomationPlanner

Responsável por transformar classificação em plano de ação.

Exemplos:

```text
category=evento, priority=alta -> planejar revisar/criar evento
category=financeiro, priority=alta -> planejar alerta financeiro
category=seguranca, priority=critica -> planejar alerta imediato
category=promocao, priority=ruido -> planejar arquivamento futuro, mas não executar em DRY_RUN
```

O planner não executa. Apenas planeja.

## 11. AutomationExecutor futuro

Executor real de ações externas.

Ações futuras:

- marcar e-mail como lido;
- arquivar;
- criar evento;
- criar tarefa;
- enviar WhatsApp;
- gerar resumo;
- pedir aprovação humana.

Todas as ações devem ser auditáveis.

Antes de executar ações mutáveis, o sistema deve suportar:

```text
DRY_RUN=true
approval_required=true
allowed_actions=[...]
```

## 12. Report

O relatório deve ser gerado a partir do estado processado, não de chamadas diretas ao conector.

Campos mínimos:

```text
schema_version
run_id
started_at
finished_at
duration_seconds
dry_run
stage_counts
accounts_total
accounts
total
total_by_account
total_by_category
total_by_priority
errors
planned_actions
```

Relatórios futuros:

- diário via WhatsApp;
- semanal por categoria;
- alertas imediatos;
- dashboard.

## 12.1 Context Engine

O Context Engine consolida dados persistidos em um `ContextSnapshot`.

Ele usa apenas:

```text
runs
emails
classifications
action_plans
WorkItems conceituais
```

Ele nao chama APIs externas, nao usa IA, nao executa automacoes e nao altera providers.

Responsabilidades:

- resumo operacional;
- ranking deterministico de prioridades;
- deteccao de follow-ups;
- lista de pessoas importantes;
- compromissos potenciais ja detectados pelo classificador;
- decisoes recentes derivadas de action plans planejados.

Futuros consumers devem acessar contexto por `ContextEngine -> ContextSnapshot`, nao diretamente pelo Firestore.

## 12.2 Security Capability

`app/security` e a camada unica de seguranca do projeto.

Responsabilidades:

- analisar headers;
- analisar links sem acessa-los;
- analisar anexos sem abri-los;
- avaliar dominios;
- produzir `SecurityAssessment`;
- gerar score e policy;
- gerar eventos internos;
- criar audit trail.

Proibido implementar seguranca propria dentro de connectors, providers, Context Engine, IA futura ou modulos de automacao.

Decisoes de policy sao apenas informativas nesta release:

```text
allow
warn
review
block
quarantine
```

## 12.3 Communication Manager

`app/communication` gerencia subscriptions sem conhecer Gmail ou Outlook diretamente.

Fluxo:

```text
EmailEntity
 -> SubscriptionDetector
 -> RFC Parser
 -> SubscriptionAggregator
 -> SubscriptionRepository
 -> RecommendationEngine
 -> ActionPlan unsubscribe_subscription
```

Regras:

- detectar nao significa confiar;
- recomendar nao significa aprovar;
- aprovar nao significa executar;
- nenhum link e acessado;
- nenhum `mailto` e enviado;
- nenhum unsubscribe e executado;
- `ActionPlan` nasce com `approval_required=true`, `execution_enabled=false` e `dry_run=true`.

## 12.4 Calendar Capability

Fluxo read-only:

```text
Google Calendar
 -> CalendarConnector
 -> CalendarEvent
 -> CalendarRepository
 -> Context Engine
 -> Daily Agenda
```

O CalendarConnector lista calendarios e eventos, mas nao cria, altera, exclui, move ou responde convites.

## 12.5 Daily Brief

Fluxo:

```text
ContextRepository
 -> ContextEngine
 -> ContextSnapshot
 -> DailyBriefBuilder
 -> DailyBrief
```

`DailyBrief` e a visao operacional consolidada do dia. Ele e diferente de `DailyAgenda`, que e centrada em compromissos. O brief nao acessa providers, nao usa IA e nao executa acoes.

## 12.6 Daily Brief Delivery

Fluxo opcional e desligado por padrao:

```text
DailyBrief
 -> Delivery Policy
 -> Email Renderer
 -> Draft or Send
 -> Delivery Audit
```

`app/daily_brief_delivery` e separado de `GmailConnector`.

Regras:

- `DAILY_BRIEF_DELIVERY_ENABLED=false` por padrao;
- `DAILY_BRIEF_DELIVERY_MODE=disabled` por padrao;
- `send` exige `DAILY_BRIEF_DELIVERY_ALLOW_SEND=true`;
- destinatario deve estar em allowlist;
- o corpo do e-mail nao e persistido;
- entrega real usa `GmailDailyBriefDeliveryClient`, que nao le inbox.

Persistencia:

```text
daily_brief_deliveries/{delivery_id}
```

Docs:

```text
docs/DAILY_BRIEF_DELIVERY.md
docs/adr/ADR-015-daily-brief-email-delivery.md
```

## 12.7 Scheduled Daily Brief

Fluxo operacional:

```text
Cloud Scheduler
 -> Cloud Run Job
 -> ScheduledDailyBriefService
 -> ContextEngine
 -> DailyBriefBuilder
 -> DailyBriefDeliveryService
 -> Scheduled Run Audit
```

O Scheduler nao contem regra de negocio. Ele apenas dispara o Job autenticado.

Regras:

- `DAILY_BRIEF_SCHEDULE_ENABLED=false` por padrao;
- modo padrao `draft`;
- `send` exige as flags de Daily Brief Delivery;
- idempotencia considera data, timezone, escopo, canal, modo, destinatario e schema;
- entrega confirmada nunca e reenviada automaticamente;
- `delivery_uncertain` exige revisao operacional;
- corpo/HTML do brief nao sao persistidos na auditoria agendada.

Docs:

```text
docs/SCHEDULED_DAILY_BRIEF.md
docs/adr/ADR-016-scheduled-daily-brief-idempotent-job.md
```

## 13. Segurança

### 13.1 Secrets

Nunca versionar:

```text
client_secret.json
refresh_token
.env
credentials.json
```

Secrets devem ficar no Secret Manager.

### 13.2 Escopos OAuth

Usar o menor escopo possível, mas preservar compatibilidade com tokens existentes.

Escopos atualmente usados:

```text
gmail.modify
calendar.events
```

Mesmo com `gmail.modify` e `calendar.events`, o código deve operar como somente leitura enquanto `DRY_RUN=true`.

Escopos opcionais de Daily Brief Delivery:

```text
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.send
```

Esses escopos sao solicitados apenas quando o operador usa `scripts/google_oauth_local.py --include-gmail-draft` ou `--include-gmail-send`.

### 13.3 Menor privilégio

Service accounts devem receber apenas permissões necessárias:

- Secret Manager Accessor;
- Firestore User;
- Cloud Run runtime;
- Logs Writer quando necessário.

## 14. Observabilidade

Toda execução deve produzir logs estruturados:

```text
run_id
account_id
provider
items_fetched
items_processed
errors_count
duration_seconds
```

Erros devem incluir:

```text
component
account_id
provider
error_type
message
stacktrace quando necessário
```

## 15. Roadmap técnico

### Sprint 1 — concluída

- Infraestrutura GCP.
- OAuth.
- Secret Manager.
- Cloud Run Job.
- Gmail funcional.
- Classificação inicial.

### Sprint 1.5 — em execução

- Pipeline desacoplado.
- EmailEntity.
- WorkItem.
- Persistence Layer.
- AutomationPlanner.
- Report consolidado.

### Sprint 2 — arquitetura Core

- Interfaces formais.
- ConnectorManager definitivo.
- AutomationExecutor interface.
- Event bus interno simples.
- ADRs iniciais.

### Sprint 3 — Google Calendar

- CalendarConnector.
- leitura de eventos;
- detecção de possíveis eventos em e-mails;
- planejamento de criação de eventos;
- execução ainda opcional.

### Sprint 4 — WhatsApp Report

- WhatsApp Cloud API.
- relatório diário.
- template aprovado.
- fallback manual.

### Sprint 5 — Outlook

- Microsoft Entra ID.
- OutlookConnector.
- normalização para EmailEntity.

### Sprint 6 — IA

- LLM provider interface.
- classificação refinada.
- resumo diário.
- priorização contextual.

### Sprint 7 — Dashboard

- visualização de runs;
- e-mails importantes;
- planos de ação;
- histórico.

## 16. Padrões proibidos

Evitar:

- lógica de Gmail dentro do DailyJob;
- Firestore sendo chamado diretamente por conectores;
- IA chamando APIs externas;
- ação mutável em DRY_RUN;
- hardcode de conta pessoal;
- duplicar modelos por provedor;
- logs sem account_id;
- relatórios baseados em strings soltas;
- mexer em infraestrutura sem necessidade real.

## 17. Padrões obrigatórios

Exigir:

- modelos internos;
- conectores isolados;
- persistência própria;
- plano de ação separado;
- logs por execução;
- upsert/idempotência;
- configuração por YAML;
- testes por camada;
- documentação atualizada a cada mudança estrutural.

## 18. Decisões arquiteturais iniciais

### ADR-001 — O núcleo não conhece provedores externos

Decisão: o núcleo opera sobre entidades de domínio e WorkItems.

Motivo: permitir Gmail, Outlook, WhatsApp, Calendar e Drive sem reescrever pipeline.

### ADR-002 — IA não executa ações

Decisão: IA classifica, resume e recomenda; execução fica com AutomationExecutor.

Motivo: segurança, auditoria e controle.

### ADR-003 — Firestore como histórico operacional inicial

Decisão: usar Firestore para runs, e-mails, classificações e planos de ação.

Motivo: simplicidade, integração nativa GCP e baixo volume inicial.

### ADR-004 — DRY_RUN como proteção padrão

Decisão: todo ambiente começa em DRY_RUN=true.

Motivo: evitar mutações acidentais em e-mail, agenda e mensagens.

### ADR-005 — WorkItem como contrato para IA futura

Decisão: todos os itens processáveis devem convergir para WorkItem.

Motivo: padronizar entrada para IA e automações.

### ADR-009 - Context Engine separado da IA

Decisao: contexto deterministico e gerado antes de IA.

Motivo: IA futura deve consumir `ContextSnapshot` consistente e auditavel, sem buscar dados diretamente em provedores ou Firestore.

### ADR-010 - Security Capability

Decisao: toda validacao de conteudo externo deve passar por `app/security`.

Motivo: evitar regras duplicadas em connectors, providers, IA ou futuros modulos.

## 19. Critério de qualidade para novas sprints

Uma sprint só deve ser considerada concluída quando:

1. O código estiver no GitHub.
2. O Cloud Run Job executar sem erro.
3. Os logs mostrarem contagens coerentes.
4. O Firestore registrar dados esperados.
5. O README/docs forem atualizados.
6. Não houver credenciais versionadas.
7. O comportamento respeitar DRY_RUN.

## 20. Próxima ação recomendada

Após o Codex concluir a Sprint 1.5:

1. Revisar PR.
2. Validar se o DailyJob deixou de conhecer Gmail diretamente.
3. Validar Firestore com estrutura nova.
4. Rodar deploy.
5. Rodar job.
6. Conferir logs.
7. Conferir Firestore.
8. Só então iniciar Sprint 2.
