# Assistente Pessoal

Assistente pessoal executado como Cloud Run Job para ler contas configuradas, normalizar mensagens, classificar, persistir, planejar acoes seguras e gerar relatorio final.

## Release 0.2 - Foundation Hardening

A Release 0.2 fortalece a fundacao antes de novos conectores:

- `EmailEntity` pode ser convertido para `WorkItem`;
- o pipeline cria `WorkItem` conceitual sem quebrar o fluxo Gmail atual;
- `ActionPlan` possui campos auditaveis;
- `Settings` centraliza projeto, regiao, `DRY_RUN`, path de contas, feature flags e limites;
- toda execucao possui `run_id` explicito;
- objetos persistidos incluem `schema_version` quando aplicavel.

Nenhuma nova integracao foi ativada nesta release.

## Release 0.3A - Multi Provider Foundation (Outlook)

A Release 0.3A prepara Outlook como segundo provider sem conectar ao Microsoft Graph real:

- `app/connectors/base.py` define a interface comum de conectores;
- `app/connectors/outlook.py` cria `OutlookConnector` em modo stub;
- `OutlookNormalizer` converte payloads fake do Microsoft Graph para `EmailEntity`;
- `EmailEntity.to_work_item()` completa o fluxo `Graph -> EmailEntity -> WorkItem`;
- `ConnectorManager` reconhece `gmail` e `outlook`;
- Outlook permanece desabilitado por padrao e nao exige credenciais Azure.

Documento tecnico:

```text
docs/OUTLOOK_DESIGN.md
```

## Release 0.3B - Microsoft Graph Integration

A Release 0.3B adiciona Outlook real em modo somente leitura, ainda desligado por padrao:

- `OAuthProvider` abstrai autenticacao;
- `MicrosoftOAuthProvider` usa MSAL e token cache serializado no Secret Manager;
- `MicrosoftGraphMailClient` le `GET /me/messages`;
- `OutlookConnector` nao conhece MSAL e retorna `EmailEntity`;
- `ConnectorManager` injeta Outlook real apenas com `OUTLOOK_ENABLED=true`;
- testes usam mocks e nao chamam Microsoft Graph.

Docs:

```text
docs/OUTLOOK_DESIGN.md
docs/setup/AZURE_SETUP.md
docs/adr/ADR-008-microsoft-graph-oauth.md
BOOTSTRAP.md
```

## Release 0.4 - Context Engine

A Release 0.4 adiciona o primeiro mecanismo de contexto sem IA:

- `ContextSnapshot` representa o estado operacional atual;
- `ContextEngine` consolida emails, classificacoes, action plans, reports e WorkItems;
- `PriorityRanker` cria ranking deterministico de prioridades;
- `FollowUpDetector` sugere acompanhamentos sem executar acoes;
- `FirestoreContextRepository` le apenas dados ja persistidos;
- nenhum provider, OAuth, conector ou infraestrutura foi alterado.

Docs:

```text
docs/CONTEXT_ENGINE.md
docs/adr/ADR-009-context-engine-separate-from-ai.md
```

## Release 0.5 - Security Foundation

A Release 0.5 cria uma Security Capability reutilizavel, sem adicionar funcionalidade de usuario:

- `ThreatAnalyzer` produz `SecurityAssessment`;
- analisadores de headers, links, anexos e dominios;
- `RiskEngine` deterministico;
- `SecurityPolicy` centralizada;
- eventos internos e audit trail;
- `ContextSnapshot` expoe `high_risk_items`, `warning_items` e `security_events`;
- nenhum link e acessado e nenhum anexo e aberto.

Docs:

```text
SECURITY.md
THREAT_MODEL.md
ENGINEERING_CONSTITUTION.md
docs/SECURITY_ARCHITECTURE.md
docs/adr/ADR-010-security-capability.md
```

## Release 0.7 - Communication Manager / Subscription Management

A Release 0.7 cria a fundacao segura para newsletters, listas e comunicacoes recorrentes:

- `SubscriptionEntity` agrega subscriptions por conta/provider;
- parser RFC interpreta headers de lista sem acessar rede;
- agregacao idempotente usa `List-ID`, dominio + target oficial ou remetente;
- subscriptions sao persistidas em `accounts/{account_id}/subscriptions/{subscription_id}`;
- recomendacao deterministica pode gerar `ActionPlan` `unsubscribe_subscription`;
- todo plano nasce `dry_run=true`, `waiting_approval`, `approval_required=true` e `execution_enabled=false`;
- alto risco de seguranca exige revisao manual;
- `scripts/subscriptions.py` lista e resume subscriptions sem executar unsubscribe.

Esta release nao acessa links, nao envia `mailto`, nao faz scraping, nao abre navegador e nao altera Gmail ou Outlook.

## Release 0.8 - Google Calendar Read-Only & Daily Agenda

A Release 0.8 adiciona leitura read-only de Google Calendar:

- `CalendarEvent` normaliza compromissos sem acoplar dominio ao Google;
- `GoogleCalendarConnector` lista calendarios e eventos com escopos read-only;
- eventos sao persistidos em `accounts/{account_id}/calendar_events/{event_id}`;
- `ContextSnapshot` expoe eventos de hoje, amanha, proximo evento, conflitos e janelas livres;
- `DailyAgendaBuilder` gera agenda diaria deterministica, sem IA;
- `scripts/calendar.py` e `make calendar` exibem agenda em modo seguro.

Escopos OAuth read-only:

```text
https://www.googleapis.com/auth/calendar.events.readonly
https://www.googleapis.com/auth/calendar.calendarlist.readonly
```

Calendar permanece desabilitado por padrao com `CALENDAR_ENABLED=false`. Mudanca de escopo pode exigir nova autorizacao e novo refresh token.

## Release 0.9 - Daily Brief v1

A Release 0.9 adiciona o primeiro brief diario consolidado:

- `DailyBrief` e `DailyBriefSection` estruturam a saida;
- `DailyBriefBuilder` consome `ContextSnapshot`, sem acessar providers;
- renderizadores texto e JSON geram saida deterministica;
- `daily_briefs/{date}:{scope}` persiste briefs de forma idempotente;
- `scripts/daily_brief.py`, `make daily-brief` e `make daily-brief-json` operam em modo seguro.

O Daily Brief nao usa IA, nao envia mensagens e nao executa ActionPlans.

## Sprint 1.5

A base foi consolidada em um pipeline desacoplado:

```text
Connector
  -> EmailEntity
  -> Classifier
  -> Persistence
  -> Automation
  -> Report
```

O `DailyJob` orquestra o fluxo e depende de abstracoes:

- `ConnectorManager`
- `Classifier`
- `Persistence`
- `AutomationPlanner`
- `Reporter`

Ele nao instancia `GmailConnector` diretamente.

## Camadas

- `app/connectors/gmail.py`: conector Gmail que retorna `EmailEntity` e nao executa mutacoes.
- `app/connectors/outlook.py`: conector Outlook read-only, desabilitado por padrao.
- `app/auth/microsoft.py`: provider OAuth Microsoft via MSAL.
- `app/integrations/microsoft_graph.py`: cliente HTTP read-only para Microsoft Graph.
- `app/connectors/manager.py`: registra conectores por provider. Hoje reconhece `gmail` e `outlook`; `outlook` permanece desabilitado salvo `OUTLOOK_ENABLED=true`.
- `app/core/models.py`: `EmailEntity`, `WorkItem`, `Classification`, `ActionPlan` e `PipelineResult`.
- `app/core/classifier.py`: classificador por regras com categoria, prioridade, confianca, motivo e `possible_event`.
- `app/storage/persistence.py`: persistencia Firestore com upsert/deduplicacao.
- `app/core/automation.py`: gera `ActionPlan` em `dry_run`, sem executar acoes reais.
- `app/core/report.py`: consolida totais e tempo de execucao.
- `app/context/*`: gera `ContextSnapshot` a partir dos dados persistidos, sem IA.
- `app/security/*`: analise estatica centralizada para conteudo externo.

## Modelos

`EmailEntity`:

```text
id, provider, account_id, account_email, thread_id, subject, sender,
recipients, snippet, labels, received_at, raw_headers, metadata
```

`WorkItem`:

```text
id, source, type, account_id, payload, created_at, schema_version
```

`ActionPlan`:

```text
type, reason, dry_run, status, payload, id, source, created_at, updated_at, audit_metadata, schema_version
```

`ActionPlan` continua sendo apenas planejado. Nao ha executor real nesta release.

`SubscriptionEntity`:

```text
subscription_id, account_id, provider, sender, sender_domain, display_name,
list_id, category, first_seen_at, last_received_at, message_count,
estimated_frequency, unsubscribe_supported, unsubscribe_methods,
unsubscribe_url, unsubscribe_email, one_click_supported, status,
recommendation_score, recommendation_reasons, latest_security_risk_level,
latest_security_risk_score, created_at, updated_at, audit_metadata,
schema_version
```

Estados `approved`, `unsubscribed` e `failed` existem apenas como contrato nesta release e nao sao produzidos automaticamente.

`ContextSnapshot`:

```text
date, generated_at, emails_pending, emails_critical, followups,
upcoming_commitments, important_people, recent_decisions, action_plans,
work_items, top_priorities, subscription_candidates, subscriptions_total,
subscriptions_active, subscriptions_new, subscriptions_recommended_for_unsubscribe,
subscriptions_waiting_approval, subscriptions_blocked_by_security,
top_subscription_candidates, summary, source_counts
```

`ContextSnapshot` e o contrato para futuros consumers de IA, Dashboard, WhatsApp e Planner.

Security:

```text
SecurityAssessment, LinkAssessment, AttachmentAssessment, HeaderAssessment,
DomainAssessment, SecurityEvent, SecurityAuditRecord
```

A Security Capability nao executa acoes. Ela apenas avalia risco, policy e eventos.

## Configuracao central

`app/config.py` centraliza:

- `PROJECT_ID`
- `REGION`
- `DRY_RUN`
- `ACCOUNTS_CONFIG_PATH`
- limites basicos, como `MAX_EMAILS_PER_PROVIDER`
- feature flags preparatorias

Feature flags iniciais:

```text
OUTLOOK_ENABLED=false
CALENDAR_ENABLED=false
WHATSAPP_ENABLED=false
AI_ENABLED=false
AUTO_EXECUTION_ENABLED=false
```

`OUTLOOK_ENABLED=false` continua sendo o comportamento esperado em producao. Com `OUTLOOK_ENABLED=true`, Outlook usa Microsoft Graph em modo somente leitura.

## Classificacao

Categorias:

```text
financeiro, compra, entrega, evento, trabalho, seguranca, promocao,
newsletter, social, educacao, viagem, saude, sistema, outros
```

Prioridades:

```text
critica, alta, normal, baixa, ruido
```

Regras importantes:

- promocao com `24h`, `oferta`, `desconto` ou percentual nao vira evento;
- tutorial nao vira evento;
- newsletter nao vira evento;
- ofertas de emprego viram `trabalho` com prioridade `normal`, salvo entrevista, convite, prazo ou resposta direta;
- recibo/compra vai para `compra` ou `financeiro`, nao para evento.

## Firestore

Estrutura:

```text
runs/{run_id}
accounts/{account_id}/emails/{message_id}
accounts/{account_id}/classifications/{message_id}
accounts/{account_id}/action_plans/{message_id}
accounts/{account_id}/subscriptions/{subscription_id}
accounts/{account_id}/calendar_events/{event_id}
daily_agendas/{date}
```

A persistencia usa merge/upsert. Emails existentes atualizam `last_seen_at`; emails novos recebem `first_seen_at`. Isso evita duplicacao por `message_id`.

O report salvo em `runs/{run_id}` possui `run_id` explicito. Emails, classificacoes e action plans recebem `run_id` quando persistidos pelo pipeline. Os objetos incluem `schema_version` para facilitar evolucao futura.

## Seguranca

`DRY_RUN=true` permanece como regra operacional. O job nao:

- marca lido;
- move mensagens;
- exclui mensagens;
- cria eventos;
- envia WhatsApp;
- executa automacoes externas.

O GmailConnector usa os escopos `gmail.modify` e `calendar.events` porque o refresh token de producao foi emitido com eles. Mesmo assim, o codigo atual apenas le mensagens e nao chama endpoints mutaveis.

## Configuracao de contas

As contas ficam em `config/accounts.yaml`. Para adicionar uma conta Gmail:

```yaml
accounts:
  - id: pessoal_google
    label: Pessoal
    provider: gmail
    email: pessoa@example.com
    enabled: true
    secret_prefix: google-pessoal
    max_emails: 10
    firestore:
      enabled: true
```

Secrets esperados:

```text
<secret_prefix>-client-secret-json
<secret_prefix>-refresh-token
```

Para adicionar uma conta Outlook:

```yaml
accounts:
  - id: profissional_outlook
    label: Profissional
    provider: outlook
    email: pessoa@example.com
    enabled: false
    secret_prefix: outlook-profissional
    max_emails: 10
```

Secrets esperados:

```text
<secret_prefix>-tenant-id
<secret_prefix>-client-id
<secret_prefix>-client-secret
<secret_prefix>-token-cache
```

## Testes

```bash
python -m pytest
```

Validacao completa:

```bash
make validate
```

O comando executa:

```bash
python -m pytest
python -m compileall app scripts
```

## Diagnostico

Use `make doctor` para validar ambiente, projeto GCP, APIs, secrets e Cloud Run Job:

```bash
make doctor
```

A saida usa:

```text
[OK]
[WARN]
[ERROR]
```

O comando falha se encontrar erros de configuracao obrigatoria.

## Subscriptions

Use `make subscriptions` para obter um resumo seguro:

```bash
make subscriptions
```

Ou diretamente:

```bash
python scripts/subscriptions.py --project-id agenda-pessoal-projeto --summary --dry-run
python scripts/subscriptions.py --project-id agenda-pessoal-projeto --recommended --json
```

O comando nao executa unsubscribe, nao acessa URLs, nao envia e-mail e redige targets sensiveis na saida.

## Calendar

Use `make calendar` para agenda diaria read-only:

```bash
make calendar
```

O comando nao cria, atualiza, exclui ou responde eventos. Meeting URLs e descricoes completas nao sao exibidas por padrao.

## Daily Brief

```bash
make daily-brief
make daily-brief-json
```

O brief usa dados persistidos via `ContextSnapshot` e nao acessa Gmail, Outlook ou Calendar diretamente.

## Validacao operacional

Depois do merge:

```bash
make validate
make doctor
make deploy
make smoke
```

Fluxo completo:

```bash
make release
```

Smoke test:

```bash
make smoke
```

O smoke executa o job, identifica a execucao, le logs para detectar erros conhecidos e validar sinais basicos. Se o report JSON estiver truncado nos logs, ele faz fallback para Firestore e exige documentos em `emails` e `classifications`; `action_plans` vazio gera `WARN`, nao falha.

Verifique no Firestore:

- novo documento em `runs`;
- documentos em `accounts/<account_id>/emails`;
- documentos em `accounts/<account_id>/classifications`;
- documentos em `accounts/<account_id>/action_plans`;
- nenhuma alteracao na caixa Gmail.

## Infraestrutura

Dockerfile, Cloud Build, Cloud Run e infraestrutura GCP permanecem inalterados. O `Makefile` apenas seleciona automaticamente `.venv/bin/python` quando disponivel e falha de forma clara se dependencias locais estiverem ausentes.
