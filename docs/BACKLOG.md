# Backlog — Assistente Pessoal

Status: vivo
Organização: por capacidade e sprint

## Sprint 1.6 — Operação mínima

Objetivo: reduzir diagnóstico manual e preparar rotina de deploy/smoke.

| Task | Prioridade | Dependência | Critério de aceite | Status |
|---|---:|---|---|---|
| 1.6.1 `make validate` | Alta | testes existentes | roda pytest e compileall | Pendente |
| 1.6.2 `make doctor` | Alta | gcloud | valida projeto, região, APIs, secrets e Cloud Run Job | Pendente |
| 1.6.3 `make smoke` | Alta | Cloud Run Job | executa job, lê logs e falha em erros conhecidos | Pendente |
| 1.6.4 docs operacionais | Média | comandos acima | README atualizado | Pendente |

## Sprint 2 — OutlookConnector

Objetivo: provar que a arquitetura aceita outro provedor de e-mail sem alterar o núcleo.

| Task | Prioridade | Dependência | Critério de aceite | Status |
|---|---:|---|---|---|
| 2.1 definir secrets Microsoft | Alta | Entra ID | documentação clara de client id/secret/refresh token | Pendente |
| 2.2 implementar OutlookConnector | Alta | msal | retorna EmailEntity | Pendente |
| 2.3 registrar no ConnectorManager | Alta | 2.2 | provider=outlook processado sem mexer em DailyJob | Pendente |
| 2.4 testes do OutlookConnector | Alta | 2.2 | mocks cobrindo normalização | Pendente |
| 2.5 config accounts.yaml | Média | 2.3 | conta outlook desabilitada por padrão | Pendente |
| 2.6 smoke em DRY_RUN | Alta | 2.5 | job executa sem ação mutável | Pendente |

## Sprint 3 — WhatsAppNotifier

Objetivo: entregar valor diário por notificação.

| Task | Prioridade | Dependência | Critério de aceite | Status |
|---|---:|---|---|---|
| 3.1 definir canal Meta WhatsApp | Alta | token/número/template | docs de setup | Pendente |
| 3.2 criar NotificationEntity | Alta | report | mensagem estruturada | Pendente |
| 3.3 WhatsAppNotifier | Alta | secrets Meta | envia ou simula envio em DRY_RUN | Pendente |
| 3.4 resumo diário textual | Alta | Report | mensagem curta e útil | Pendente |
| 3.5 Scheduler diário | Alta | Cloud Scheduler | roda diariamente | Pendente |
| 3.6 smoke de notificação | Alta | 3.3 | logs mostram payload sem envio real em DRY_RUN | Pendente |

## Sprint 4 — Calendar Intelligence

Objetivo: ler agenda e planejar eventos a partir de e-mails.

| Task | Prioridade | Dependência | Critério de aceite | Status |
|---|---:|---|---|---|
| 4.1 CalendarConnector read-only | Alta | OAuth calendar | normaliza CalendarEventEntity | Pendente |
| 4.2 detectar evento em EmailEntity | Alta | classifier | ActionPlan de evento | Pendente |
| 4.3 conflito de agenda | Média | CalendarConnector | identifica sobreposição | Pendente |
| 4.4 criar plano de criação de evento | Alta | AutomationPlanner | sem execução real em DRY_RUN | Pendente |
| 4.5 executor futuro de evento | Baixa | AutomationExecutor | interface, sem mutação inicial | Pendente |

## Sprint 5 — IA

Objetivo: melhorar classificação e resumo sem acoplar modelo.

| Task | Prioridade | Dependência | Critério de aceite | Status |
|---|---:|---|---|---|
| 5.1 LLMProvider interface | Alta | WorkItem | sem dependência direta de SDK no domínio | Pendente |
| 5.2 OpenAIProvider | Média | secret | classifica/sumariza via interface | Pendente |
| 5.3 cache de resposta | Média | persistence | evita custo repetido | Pendente |
| 5.4 prompt policy | Alta | PRD | regras de uso e não uso | Pendente |
| 5.5 avaliação humana | Média | dashboard/report | campo de feedback | Pendente |

## Sprint 6 — Dashboard

Objetivo: visualização operacional.

| Task | Prioridade | Dependência | Critério de aceite | Status |
|---|---:|---|---|---|
| 6.1 definir stack | Média | PRD | decisão registrada | Pendente |
| 6.2 endpoint/read model | Alta | Firestore | dados agregados por run | Pendente |
| 6.3 tela inicial | Média | stack | cards de status | Pendente |
| 6.4 timeline de ações | Média | action_plans | filtros por status | Pendente |

## Dívida técnica conhecida

| Item | Prioridade | Resolução |
|---|---:|---|
| Escopos OAuth atuais usam `gmail.modify` por compatibilidade do refresh token | Média | rotacionar token futuramente com escopo mínimo quando possível |
| `make deploy make run-job` causa erro de alvo | Baixa | documentar e criar `make release` |
| Validação Firestore ainda manual | Média | incluir em `make smoke` |
| Codex possui limite de uso | Alta | tasks pequenas e prompts enxutos |

## Próxima task operacional

Task 1.6.1–1.6.3 devem ser implementadas juntas, pois são pequenas e reduzem atrito imediatamente.
