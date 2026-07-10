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
high_risk_items
warning_items
security_events
subscriptions_total
subscriptions_active
subscriptions_new
subscriptions_recommended_for_unsubscribe
subscriptions_waiting_approval
subscriptions_blocked_by_security
top_subscription_candidates
calendar_events_today
calendar_events_tomorrow
calendar_events_upcoming
all_day_events_today
next_event
meetings_count_today
free_windows_today
calendar_conflicts
declined_events
calendar_security_warnings
```

`summary` contem:

```text
total_emails
critical_emails
followups
pending_action_plans
subscriptions_total
subscriptions_active
subscriptions_new
subscriptions_recommended_for_unsubscribe
subscriptions_waiting_approval
subscriptions_blocked_by_security
subscription_summary_lines
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
- `accounts/{account_id}/subscriptions`;
- `accounts/{account_id}/calendar_events`;
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

## Security Foundation

A partir da Release 0.5, o snapshot tambem expoe assessments e eventos de seguranca:

```text
high_risk_items
warning_items
security_events
```

Esses campos sao derivados de `ThreatAnalyzer` e nao executam bloqueio, quarentena, unsubscribe ou qualquer acao automatica.

## Communication Manager

A partir da Release 0.7, o snapshot tambem expoe contagens de subscriptions persistidas e candidatos principais para revisao.

O resumo operacional inclui frases deterministicas, por exemplo:

```text
Foram identificadas 12 inscricoes.
4 sao candidatas a cancelamento.
1 exige revisao de seguranca.
```

URLs e enderecos sensiveis de unsubscribe nao entram no resumo.

## Calendar

A Release 0.8 adiciona eventos persistidos ao Context Engine.

O Context Engine nao chama Google Calendar. Ele calcula de forma deterministica:

- eventos de hoje e amanha;
- proximo compromisso;
- eventos de dia inteiro;
- janelas livres;
- conflitos;
- eventos declined;
- alertas de seguranca de calendario.
