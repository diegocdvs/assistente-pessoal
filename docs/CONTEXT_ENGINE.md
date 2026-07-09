# Context Engine - Release 0.4

Status: implementado sem IA  
Escopo: consolidar dados persistidos em um `ContextSnapshot`.

## Objetivo

O Context Engine produz uma visao operacional do usuario a partir dos dados ja existentes no sistema. Ele nao chama Gmail, Outlook, Microsoft Graph, APIs externas ou LLMs.

Fluxo:

```text
Firestore / dados persistidos
        |
        v
ContextRepository
        |
        v
ContextEngine
        |
        v
ContextSnapshot
        |
        v
Futuros consumers: IA, Dashboard, WhatsApp, Planner
```

## API

Uso esperado:

```python
from app.context import ContextEngine, FirestoreContextRepository

repository = FirestoreContextRepository(project_id="agenda-pessoal-projeto")
snapshot = ContextEngine(repository).build_snapshot(account_ids=["pessoal_google"])
payload = snapshot.to_dict()
```

Consumers devem usar `ContextEngine` e `ContextSnapshot`, nao consultar Firestore diretamente quando precisam de contexto.

## ContextSnapshot

Campos principais:

```text
date
generated_at
window_days
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

`summary` contem:

```text
total_emails
critical_emails
followups
pending_action_plans
top_category
top_priority
total_by_category
total_by_priority
```

## Dados utilizados

O Context Engine usa apenas:

- `accounts/{account_id}/emails`;
- `accounts/{account_id}/classifications`;
- `accounts/{account_id}/action_plans`;
- `runs/{run_id}`;
- `WorkItem` conceitual reconstruido a partir dos emails persistidos.

## Priority Ranking

`PriorityRanker` pontua cada WorkItem por:

- prioridade da classificacao;
- categoria;
- idade;
- action plans associados;
- status de follow-up.

Pesos iniciais:

```text
critica=100
alta=70
normal=35
baixa=10
ruido=-20
```

Categorias sensiveis, como `seguranca`, `financeiro`, `saude`, `trabalho` e `evento`, aumentam a pontuacao. Promocoes e newsletters reduzem a pontuacao.

## Follow-up Detector

`FollowUpDetector` gera sugestoes sem executar acoes.

Tipos iniciais:

```text
sent_without_reply
old_pending
forgotten_work_item
```

Heuristicas:

- email com label `SENT` ou metadata `direction=sent`, sem resposta posterior na thread, gera sugestao apos 3 dias;
- item relevante antigo gera `old_pending` apos 7 dias;
- WorkItem antigo sem classificacao nem action plan gera `forgotten_work_item`.

## Resumo Operacional

O resumo e deterministico:

```text
Hoje:
- total de emails
- emails criticos
- follow-ups
- action plans pendentes
- categoria dominante
- prioridade dominante
```

Nao ha IA, prompt, embedding, vetor ou chamada a modelo.

## Limites

Nao implementado:

- IA;
- Calendar;
- WhatsApp;
- Dashboard;
- planner real;
- banco novo;
- vetores/embeddings;
- novas integracoes.

## Futuro

A IA futura deve receber `ContextSnapshot` como entrada. Ela nao deve buscar dados diretamente no Firestore, Gmail, Outlook, Calendar ou WhatsApp.
