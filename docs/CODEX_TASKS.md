# Codex Tasks — prompts prontos

Use estes prompts quando o Codex estiver disponível. Cada task deve ser executada isoladamente.

## Task 1.6 — Operação mínima

```text
Implemente a Sprint 1.6 seguindo:
- docs/NORTH_STAR.md
- docs/MASTER_ARCHITECTURE.md
- docs/PRD.md
- docs/ENGINEERING_PLAYBOOK.md
- docs/RUNBOOK.md

Escopo:
Criar comandos operacionais mínimos no Makefile:
- make validate
- make doctor
- make smoke

Requisitos:
1. make validate deve executar:
   - python -m pytest
   - python -m compileall app scripts

2. make doctor deve verificar:
   - gcloud instalado
   - projeto GCP ativo agenda-pessoal-projeto
   - região southamerica-east1
   - APIs habilitadas:
     - run.googleapis.com
     - cloudbuild.googleapis.com
     - artifactregistry.googleapis.com
     - secretmanager.googleapis.com
     - firestore.googleapis.com
     - gmail.googleapis.com
   - secrets existentes:
     - google-pessoal-client-secret-json
     - google-pessoal-refresh-token
   - Cloud Run Job:
     - assistente-pessoal-diario

3. make smoke deve:
   - executar o job
   - capturar a última execução
   - ler logs
   - falhar se encontrar:
     - invalid_scope
     - accessNotConfigured
     - RefreshError
     - HttpError 403
     - MVP placeholder ativo
   - validar que o report final não possui errors

4. Atualizar README com os comandos.
5. Não alterar GmailConnector.
6. Não alterar OAuth.
7. Não alterar arquitetura principal.
8. Não alterar infraestrutura, salvo Makefile/scripts auxiliares.

Validação:
python -m pytest
python -m compileall app scripts
make validate

Ao final, abrir PR ou informar commits.
```

## Task 2.1 — Preparação Outlook

```text
Prepare a base do OutlookConnector seguindo os documentos do projeto.

Escopo:
- documentar secrets necessários para Microsoft/Outlook;
- adicionar exemplo desabilitado em config/accounts.yaml;
- criar esqueleto OutlookConnector sem chamada real se credenciais não existirem;
- criar testes de normalização com payload fake.

Fora de escopo:
- OAuth Microsoft real;
- deploy;
- alteração de DailyJob.

Critério de aceite:
- provider=outlook é reconhecido pelo ConnectorManager quando registrado;
- nenhum erro ocorre com conta outlook disabled;
- testes passam.
```

## Task 3.1 — WhatsAppNotifier base

```text
Criar base do WhatsAppNotifier para envio futuro de resumo diário.

Escopo:
- NotificationEntity;
- WhatsAppNotifier interface;
- implementação dry-run que apenas loga payload;
- formato de resumo diário a partir do Report.

Fora de escopo:
- envio real pela Meta API;
- leitura de mensagens WhatsApp;
- Cloud Scheduler.

Critério de aceite:
- DRY_RUN não envia mensagem real;
- payload aparece nos logs;
- testes passam.
```
