# Backlog - Assistente Pessoal

Status: vivo
Organizacao: por capacidade e sprint

## Release 0.2 - Foundation Hardening

Objetivo: fortalecer contratos e operacao antes de novos conectores.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 0.2.1 WorkItem central | Alta | EmailEntity | EmailEntity converte para WorkItem e pipeline registra work item conceitual | Concluido |
| 0.2.2 ActionPlan auditavel | Alta | AutomationPlanner | ActionPlan tem id, source, timestamps, dry_run, status, payload e audit_metadata | Concluido |
| 0.2.3 Config centralizada | Alta | Settings | PROJECT_ID, REGION, DRY_RUN, path de contas, flags e limites em app/config.py | Concluido |
| 0.2.4 Feature flags | Media | Config centralizada | flags futuras existem e permanecem desligadas por padrao | Concluido |
| 0.2.5 Observabilidade minima | Alta | DailyJob | run_id, contagens por etapa e schema_version persistidos | Concluido |
| 0.2.6 Documentacao | Media | itens acima | README, arquitetura, runbook, backlog e review atualizados | Concluido |

## Release 0.3A - Multi Provider Foundation (Outlook)

Objetivo: preparar Outlook como segundo provider sem conectar ao Microsoft Graph real.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 0.3A.1 Interface comum de conectores | Alta | ConnectorManager | todos os conectores usam contrato comum `fetch_recent -> list[EmailEntity]` | Concluido |
| 0.3A.2 OutlookConnector stub | Alta | interface comum | provider `outlook` existe sem chamadas reais ao Graph | Concluido |
| 0.3A.3 Outlook models/config | Media | OutlookConnector | modelos simples `OutlookAccount` e `OutlookConfig` existem | Concluido |
| 0.3A.4 ConnectorManager multi-provider | Alta | OutlookConnector | reconhece `gmail` e `outlook`; Outlook permanece desabilitado | Concluido |
| 0.3A.5 Payloads fake Graph | Alta | OutlookNormalizer | testes validam `Graph -> EmailEntity -> WorkItem` | Concluido |
| 0.3A.6 Outlook design doc | Media | itens acima | `docs/OUTLOOK_DESIGN.md` criado | Concluido |

## Sprint 1.6 - Operacao minima

Objetivo: reduzir diagnostico manual e preparar rotina de deploy/smoke.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 1.6.1 `make validate` | Alta | testes existentes | roda pytest e compileall | Concluido |
| 1.6.2 `make doctor` | Alta | gcloud | valida projeto, regiao, APIs, secrets e Cloud Run Job | Concluido |
| 1.6.3 `make smoke` | Alta | Cloud Run Job | executa job, le logs, falha em erros conhecidos e usa fallback Firestore | Concluido |
| 1.6.4 docs operacionais | Media | comandos acima | README atualizado | Concluido |
| 1.6.5 `make release` | Alta | comandos operacionais | encadeia validate, doctor, deploy e smoke | Concluido |

## Sprint 2 - OutlookConnector

Objetivo: provar que a arquitetura aceita outro provedor de e-mail sem alterar o nucleo.

Observacao: a Release 0.3B implementou leitura real read-only do Microsoft Graph atras de `OUTLOOK_ENABLED=false` por padrao. Permanecem pendentes bootstrap operacional de credenciais, validacao em Cloud Run e evolucoes fora de leitura.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 2.1 definir secrets Microsoft | Alta | Entra ID | documentacao clara de tenant/client/token-cache | Concluido |
| 2.2 implementar OutlookConnector | Alta | msal | retorna EmailEntity | Concluido |
| 2.3 registrar no ConnectorManager | Alta | 2.2 | provider=outlook processado sem mexer em DailyJob | Concluido |
| 2.4 testes do OutlookConnector | Alta | 2.2 | mocks cobrindo normalizacao, OAuth e Graph | Concluido |
| 2.5 config accounts.yaml | Media | 2.3 | conta outlook desabilitada por padrao | Pendente |
| 2.6 smoke em DRY_RUN | Alta | 2.5 | job executa sem acao mutavel | Pendente |
| 2.7 bootstrap OAuth Microsoft | Alta | Azure | script/processo para gerar MSAL token cache | Pendente |

## Sprint 3 - WhatsAppNotifier

Objetivo: entregar valor diario por notificacao.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 3.1 definir canal Meta WhatsApp | Alta | token/numero/template | docs de setup | Pendente |
| 3.2 criar NotificationEntity | Alta | report | mensagem estruturada | Pendente |
| 3.3 WhatsAppNotifier | Alta | secrets Meta | envia ou simula envio em DRY_RUN | Pendente |
| 3.4 resumo diario textual | Alta | Report | mensagem curta e util | Pendente |
| 3.5 Scheduler diario | Alta | Cloud Scheduler | roda diariamente | Pendente |
| 3.6 smoke de notificacao | Alta | 3.3 | logs mostram payload sem envio real em DRY_RUN | Pendente |

## Release 0.4 - Context Engine

Objetivo: criar contexto operacional deterministico antes de IA, Dashboard e WhatsApp.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 0.4.1 ContextSnapshot | Alta | modelos de dominio | snapshot serializavel com resumo, prioridades e followups | Concluido |
| 0.4.2 ContextEngine | Alta | Firestore/read models | monta snapshot sem chamar APIs externas | Concluido |
| 0.4.3 Priority Ranking | Alta | classificacoes/action plans | ordena WorkItems por prioridade, categoria, idade, plano e follow-up | Concluido |
| 0.4.4 Follow-up Detector | Alta | emails/workitems | detecta enviados sem resposta, pendencias antigas e itens esquecidos | Concluido |
| 0.4.5 Documentacao e ADR | Media | implementacao | `docs/CONTEXT_ENGINE.md` e ADR-009 criados | Concluido |

## Release 0.5 - Security Foundation

Objetivo: criar camada unica de seguranca para todos os providers e consumers futuros.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 0.5.1 ThreatAnalyzer | Alta | modelos de dominio | produz `SecurityAssessment` sem modificar dados | Concluido |
| 0.5.2 Header/Link/Attachment/Domain analyzers | Alta | ThreatAnalyzer | analise estatica sem acessar links/anexos | Concluido |
| 0.5.3 Risk Engine e Policy | Alta | assessments | score deterministico e decisao allow/warn/review/quarantine | Concluido |
| 0.5.4 Security Events e Audit Trail | Alta | Risk Engine | eventos internos e `SecurityAuditRecord` serializaveis | Concluido |
| 0.5.5 ContextSnapshot security fields | Media | Context Engine | expõe high risk, warning e security events | Concluido |
| 0.5.6 Docs e ADR-010 | Media | implementacao | SECURITY, THREAT_MODEL, arquitetura e ADR criados | Concluido |

## Sprint 4 - Calendar Intelligence

Objetivo: ler agenda e planejar eventos a partir de e-mails.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 4.1 CalendarConnector read-only | Alta | OAuth calendar | normaliza CalendarEventEntity | Pendente |
| 4.2 detectar evento em EmailEntity | Alta | classifier | ActionPlan de evento | Pendente |
| 4.3 conflito de agenda | Media | CalendarConnector | identifica sobreposicao | Pendente |
| 4.4 criar plano de criacao de evento | Alta | AutomationPlanner | sem execucao real em DRY_RUN | Pendente |
| 4.5 executor futuro de evento | Baixa | AutomationExecutor | interface, sem mutacao inicial | Pendente |

## Sprint 5 - IA

Objetivo: melhorar classificacao e resumo sem acoplar modelo.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 5.1 LLMProvider interface | Alta | WorkItem | sem dependencia direta de SDK no dominio | Pendente |
| 5.2 OpenAIProvider | Media | secret | classifica/sumariza via interface | Pendente |
| 5.3 cache de resposta | Media | persistence | evita custo repetido | Pendente |
| 5.4 prompt policy | Alta | PRD | regras de uso e nao uso | Pendente |
| 5.5 avaliacao humana | Media | dashboard/report | campo de feedback | Pendente |

## Sprint 6 - Dashboard

Objetivo: visualizacao operacional.

| Task | Prioridade | Dependencia | Criterio de aceite | Status |
|---|---:|---|---|---|
| 6.1 definir stack | Media | PRD | decisao registrada | Pendente |
| 6.2 endpoint/read model | Alta | Firestore | dados agregados por run | Pendente |
| 6.3 tela inicial | Media | stack | cards de status | Pendente |
| 6.4 timeline de acoes | Media | action_plans | filtros por status | Pendente |

## Divida tecnica conhecida

| Item | Prioridade | Resolucao |
|---|---:|---|
| Escopos OAuth atuais usam `gmail.modify` e `calendar.events` por compatibilidade do refresh token | Media | rotacionar token futuramente com escopo minimo quando possivel |
| `make deploy make run-job` causa erro de alvo | Baixa | resolvido por `make release` |
| Validacao Firestore ainda manual | Media | smoke usa fallback Firestore para emails e classifications |
| Codex possui limite de uso | Alta | tasks pequenas e prompts enxutos |
| `WorkItem` nao participava do pipeline real | Alta | Release 0.2 cria WorkItem conceitual a partir de EmailEntity |
| `ActionPlan` tinha pouca auditabilidade | Alta | Release 0.2 adiciona id, source, timestamps e audit_metadata |
| Observabilidade nao tinha run_id explicito | Alta | Release 0.2 adiciona run_id e contagens por etapa |

## Proxima release recomendada

Release 0.3 deve provar multi-conta real antes de novos dominios ou automacoes mutaveis.
