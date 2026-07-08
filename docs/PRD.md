# PRD — Assistente Pessoal

## 1. Visão

O Assistente Pessoal é uma plataforma de automação pessoal que coleta informações de canais diversos, normaliza esses dados, classifica relevância, persiste histórico, planeja ações e comunica prioridades ao usuário.

A primeira versão deve funcionar como um assistente operacional diário, não como uma IA conversacional genérica.

## 2. Usuário-alvo

Usuário individual com alta carga de informação, múltiplas contas, projetos profissionais e necessidade de acompanhamento diário de e-mails, agenda, prazos, cobranças e compromissos.

## 3. Casos de uso principais

### UC-001 — Resumo diário

Todo dia pela manhã, o sistema lê fontes conectadas, consolida prioridades e envia um resumo curto por WhatsApp.

### UC-002 — Triagem de e-mail

O sistema lê Gmail e Outlook, classifica mensagens e separa ruído de itens importantes.

### UC-003 — Planejamento de ações

O sistema transforma itens relevantes em `ActionPlan`, sem executar automaticamente em `DRY_RUN`.

### UC-004 — Detecção de eventos

E-mails com compromissos, convites, entrevistas ou prazos devem gerar planos de revisão/criação de evento.

### UC-005 — Histórico operacional

Todas as execuções, mensagens, classificações e planos devem ficar persistidos no Firestore.

## 4. Requisitos funcionais

### RF-001 — Conectores

O sistema deve suportar múltiplos provedores por meio de conectores isolados.

Conectores prioritários:

1. Gmail — concluído.
2. Outlook — próxima integração.
3. Google Calendar.
4. WhatsApp como canal de notificação.
5. Google Drive.

### RF-002 — Normalização

Cada conector deve normalizar dados para entidades internas, como `EmailEntity` e `WorkItem`.

### RF-003 — Classificação

O sistema deve classificar por categoria e prioridade.

Categorias iniciais:

- financeiro
- compra
- entrega
- evento
- trabalho
- seguranca
- promocao
- newsletter
- social
- educacao
- viagem
- saude
- sistema
- outros

Prioridades:

- critica
- alta
- normal
- baixa
- ruido

### RF-004 — Persistência

Persistir:

- runs;
- e-mails;
- classificações;
- planos de ação;
- metadados de execução.

### RF-005 — Automação planejada

Gerar `ActionPlan`, mas não executar ações externas enquanto `DRY_RUN=true`.

### RF-006 — Notificação

Enviar resumo diário por WhatsApp quando o módulo de notificação estiver implementado.

## 5. Requisitos não funcionais

### RNF-001 — Segurança

Credenciais nunca devem ser versionadas. Todos os segredos ficam no Secret Manager.

### RNF-002 — Idempotência

Processar o mesmo item mais de uma vez não deve duplicar documentos.

### RNF-003 — Observabilidade

Toda execução deve registrar logs com `run_id`, conta, provedor, duração, contagens e erros.

### RNF-004 — Extensibilidade

Novos provedores devem entrar sem reescrever o núcleo.

### RNF-005 — Operabilidade

O projeto deve ter comandos para validar ambiente, deploy, smoke test e diagnóstico.

## 6. MVP já concluído

- Cloud Run Job.
- Gmail funcional.
- OAuth e Secret Manager.
- Firestore.
- AccountManager.
- ConnectorManager.
- Classifier.
- Persistence.
- AutomationPlanner.
- Report.

## 7. Versão 1.0

A versão 1.0 exige:

- Gmail funcionando;
- Outlook funcionando;
- Calendar lendo agenda;
- WhatsApp enviando resumo diário;
- Scheduler diário;
- comandos `make doctor`, `make validate`, `make smoke`;
- relatório persistido e auditável.

## 8. Métricas de sucesso

- Execução diária sem erro por 7 dias consecutivos.
- Tempo de execução inferior a 60 segundos para carga inicial pequena.
- Zero ações mutáveis executadas em `DRY_RUN`.
- Resumo diário útil recebido por WhatsApp.
- Redução de tempo manual de triagem.

## 9. Roadmap funcional

1. Sprint 1.6 — Operação: validate, doctor, smoke.
2. Sprint 2 — OutlookConnector.
3. Sprint 3 — WhatsAppNotifier.
4. Sprint 4 — Calendar Intelligence.
5. Sprint 5 — IA.
6. Sprint 6 — Dashboard.
