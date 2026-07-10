# Codex Tasks - prompts prontos

Use estes prompts quando o Codex estiver disponivel. Cada task deve ser executada isoladamente.

## Release 0.9 - Daily Brief v1

```text
Implementar Daily Brief deterministico:
- DailyBrief e DailyBriefSection;
- DailyBriefBuilder a partir de ContextSnapshot;
- renderizacao texto e JSON;
- repository in-memory e Firestore;
- scripts/daily_brief.py;
- make daily-brief e make daily-brief-json;
- docs/DAILY_BRIEF.md;
- ADR-014.

Nao usar IA, nao acessar providers e nao executar acoes.
```

## Release 0.8 - Google Calendar Read-Only

```text
Implementar Calendar read-only sem criar eventos:
- CalendarEvent;
- GoogleCalendarConnector read-only;
- CalendarRepository;
- ContextSnapshot com agenda;
- DailyAgendaBuilder deterministico;
- scripts/calendar.py e make calendar;
- docs/CALENDAR_ARCHITECTURE.md;
- docs/setup/GOOGLE_CALENDAR_SETUP.md;
- ADR-013.

Validacao:
python -m pytest
python -m compileall app scripts
git diff --check
```

## Task 1.6 - Operacao minima

```text
Implemente a Sprint 1.6 seguindo:
- docs/NORTH_STAR.md
- docs/MASTER_ARCHITECTURE.md
- docs/PRD.md
- docs/ENGINEERING_PLAYBOOK.md
- docs/RUNBOOK.md

Escopo:
Criar comandos operacionais minimos no Makefile:
- make validate
- make doctor
- make smoke
- make release

Requisitos:
1. make validate deve executar:
   - python -m pytest
   - python -m compileall app scripts

2. make doctor deve verificar:
   - Python instalado
   - pip instalado
   - ambiente virtual ativo (.venv)
   - Docker instalado
   - gcloud instalado
   - autenticacao valida
   - projeto GCP ativo agenda-pessoal-projeto
   - regiao southamerica-east1
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
   - capturar a ultima execucao
   - ler logs
   - falhar se encontrar:
     - invalid_scope
     - accessNotConfigured
     - RefreshError
     - HttpError 403
     - MVP placeholder ativo
   - validar que o report final nao possui errors quando o JSON estiver disponivel
   - usar fallback Firestore quando os logs estiverem truncados
   - exigir documentos em accounts/pessoal_google/emails
   - exigir documentos em accounts/pessoal_google/classifications
   - tratar action_plans vazio como WARN

4. make release deve executar:
   - make validate
   - make doctor
   - make deploy
   - make smoke

5. Atualizar README com os comandos.
6. Nao alterar GmailConnector.
7. Nao alterar OAuth.
8. Nao alterar arquitetura principal.
9. Nao alterar infraestrutura, salvo Makefile/scripts auxiliares.

Validacao:
python -m pytest
python -m compileall app scripts
make validate

Ao final, abrir PR ou informar commits.
```

## Task 2.1 - Preparacao Outlook

```text
Prepare a base do OutlookConnector seguindo os documentos do projeto.

Escopo:
- documentar secrets necessarios para Microsoft/Outlook;
- adicionar exemplo desabilitado em config/accounts.yaml;
- criar esqueleto OutlookConnector sem chamada real se credenciais nao existirem;
- criar testes de normalizacao com payload fake.

Fora de escopo:
- OAuth Microsoft real;
- deploy;
- alteracao de DailyJob.

Criterio de aceite:
- provider=outlook e reconhecido pelo ConnectorManager quando registrado;
- nenhum erro ocorre com conta outlook disabled;
- testes passam.
```

## Task 3.1 - WhatsAppNotifier base

```text
Criar base do WhatsAppNotifier para envio futuro de resumo diario.

Escopo:
- NotificationEntity;
- WhatsAppNotifier interface;
- implementacao dry-run que apenas loga payload;
- formato de resumo diario a partir do Report.

Fora de escopo:
- envio real pela Meta API;
- leitura de mensagens WhatsApp;
- Cloud Scheduler.

Criterio de aceite:
- DRY_RUN nao envia mensagem real;
- payload aparece nos logs;
- testes passam.
```
