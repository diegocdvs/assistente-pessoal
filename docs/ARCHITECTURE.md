# Arquitetura do Assistente Pessoal

## Pipeline

```text
Connector
  -> EmailEntity
  -> Classifier
  -> Persistence
  -> Automation
  -> Report
  -> ContextEngine
  -> ContextSnapshot
```

A Sprint 1.5 separa integracoes externas, dominio, classificacao, persistencia, planejamento de automacao e relatorio. A meta e preparar a base para Calendar, Outlook, WhatsApp e IA sem acoplamento ao Gmail.

## DailyJob

`app/core/daily_job.py` e apenas o orquestrador. Ele depende de contratos:

- `ConnectorManagerProtocol`
- `ClassifierProtocol`
- `PersistenceProtocol`
- `AutomationPlannerProtocol`
- `ReporterProtocol`

As implementacoes padrao sao montadas no construtor, mas o job nao instancia `GmailConnector` diretamente.

## ConnectorManager

`app/connectors/manager.py` registra conectores por provider.

- `gmail`: implementado via `GmailConnector`.
- `outlook`: stub implementado via `OutlookConnector`, desabilitado por padrao.
- `calendar`: provider planejado.
- `whatsapp`: provider planejado.

Conectores retornam `EmailEntity` ou entidade equivalente de dominio, nunca payload cru da API externa.

Na Release 0.3A, payloads fake do Microsoft Graph sao normalizados por `OutlookNormalizer` para `EmailEntity` e depois convertidos para `WorkItem`. Nao ha chamada real ao Graph.

## EmailEntity

Modelo interno normalizado:

```text
id, provider, account_id, account_email, thread_id, subject, sender,
recipients, snippet, labels, received_at, raw_headers, metadata
```

Detalhes especificos do Gmail ficam em `metadata`.

## WorkItem

Modelo generico para futuras filas e automacoes:

```text
id, source, type, account_id, payload, created_at
```

## Classifier

`RuleBasedClassifier` retorna:

- `category`
- `priority`
- `confidence`
- `reason`
- `possible_event`

Categorias:

```text
financeiro, compra, entrega, evento, trabalho, seguranca, promocao,
newsletter, social, educacao, viagem, saude, sistema, outros
```

Prioridades:

```text
critica, alta, normal, baixa, ruido
```

Regras evitam falsos positivos de eventos em promocoes, newsletters, tutoriais e recibos.

## Persistence

`app/storage/persistence.py` oferece:

- `save_run`
- `save_email`
- `save_classification`
- `save_action_plan`
- `upsert_email`

Estrutura Firestore:

```text
runs/{run_id}
accounts/{account_id}/emails/{message_id}
accounts/{account_id}/classifications/{message_id}
accounts/{account_id}/action_plans/{message_id}
```

`save_email` usa merge/upsert por `message_id`; documentos existentes atualizam `last_seen_at`, documentos novos recebem `first_seen_at`.

## AutomationPlanner

`app/core/automation.py` gera planos, mas nao executa acoes reais.

`ActionPlan`:

```text
type, reason, dry_run, status, payload
```

## Report

`app/core/report.py` gera:

- total por conta;
- total por categoria;
- total por prioridade;
- erros;
- acoes planejadas;
- duracao da execucao.

## Context Engine

`app/context` gera `ContextSnapshot` a partir de dados ja persistidos. Ele nao chama APIs externas e nao usa IA.

Responsabilidades:

- resumo operacional;
- ranking de prioridades;
- deteccao de follow-ups;
- consolidacao de WorkItems, action plans, classificacoes e reports.

Futuros consumers devem usar `ContextEngine -> ContextSnapshot` em vez de consultar Firestore diretamente.

## Seguranca

O pipeline segue somente leitura:

- nao marcar lido;
- nao mover;
- nao excluir;
- nao criar evento;
- nao enviar WhatsApp.

`DRY_RUN=true` deve permanecer ativo enquanto as automacoes reais nao forem explicitamente projetadas e testadas.
