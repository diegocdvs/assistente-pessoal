# Bootstrap

## Ambiente Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

O `Makefile` usa `.venv/bin/python` automaticamente quando existir. Se `pytest` nao estiver instalado, `make validate` aborta com uma mensagem clara.

## Validacao local

```bash
python -m pytest
python -m compileall app scripts
```

## Context Engine

O Context Engine nao exige credenciais novas. Ele usa apenas dados ja persistidos:

```python
from app.context import ContextEngine, FirestoreContextRepository

repository = FirestoreContextRepository(project_id="agenda-pessoal-projeto")
snapshot = ContextEngine(repository).build_snapshot(account_ids=["pessoal_google"])
print(snapshot.to_dict())
```

Nao ha IA, LLM, embeddings ou novas integracoes nesta release.

## Security Foundation

A Security Capability nao exige credenciais novas:

```python
from app.security import ThreatAnalyzer

assessment = ThreatAnalyzer().analyze(email_payload)
print(assessment.to_dict())
```

Ela nunca acessa links, nunca abre anexos e nunca executa acoes automaticamente.

## Communication Manager

Subscriptions podem ser inspecionadas em modo seguro:

```bash
python scripts/subscriptions.py --project-id agenda-pessoal-projeto --summary --dry-run
```

Garantias da Release 0.7:

- nao executa unsubscribe;
- nao acessa URLs;
- nao envia `mailto`;
- nao faz scraping;
- nao abre navegador;
- nao altera Gmail ou Outlook;
- gera apenas planos de acao com aprovacao obrigatoria e execucao desligada.

## Gmail

Gmail continua usando Secret Manager com:

```text
<secret_prefix>-client-secret-json
<secret_prefix>-refresh-token
```

O conector le mensagens e nao executa mutacoes.

## Outlook

Outlook permanece desligado por padrao:

```bash
OUTLOOK_ENABLED=false
```

Para preparar uma conta Outlook, consulte:

```text
docs/setup/AZURE_SETUP.md
```

Secrets esperados:

```text
<secret_prefix>-tenant-id
<secret_prefix>-client-id
<secret_prefix>-client-secret
<secret_prefix>-token-cache
```

Ative somente em ambiente controlado:

```bash
OUTLOOK_ENABLED=true
```

Mesmo ativo, o conector Outlook e somente leitura.

## Google Calendar

Calendar permanece desligado por padrao:

```bash
CALENDAR_ENABLED=false
```

Para reautorizar OAuth com Calendar read-only:

```bash
python scripts/google_oauth_local.py --client-secret-file client_secret.json --include-calendar-readonly
```

Escopos usados:

```text
https://www.googleapis.com/auth/calendar.events.readonly
https://www.googleapis.com/auth/calendar.calendarlist.readonly
```

Validacao read-only:

```bash
python scripts/calendar.py --project-id agenda-pessoal-projeto --daily-agenda --dry-run
```

## Daily Brief

```bash
python scripts/daily_brief.py --project-id agenda-pessoal-projeto --dry-run
python scripts/daily_brief.py --project-id agenda-pessoal-projeto --json --no-persist
```

O Daily Brief consome `ContextSnapshot`, nao chama providers e nao executa acoes.

## Daily Brief Delivery

Daily Brief Delivery permanece desligado por padrao:

```bash
DAILY_BRIEF_DELIVERY_ENABLED=false
DAILY_BRIEF_DELIVERY_MODE=disabled
DAILY_BRIEF_DELIVERY_ALLOW_SEND=false
```

Validacao segura:

```bash
python scripts/daily_brief_delivery.py --project-id agenda-pessoal-projeto --use-last-brief --json
python scripts/daily_brief_delivery.py --project-id agenda-pessoal-projeto --mode draft --dry-run --use-last-brief --json
```

Para preparar OAuth de rascunho ou envio:

```bash
python scripts/google_oauth_local.py --client-secret-file client_secret.json --include-gmail-draft
python scripts/google_oauth_local.py --client-secret-file client_secret.json --include-gmail-send
```

Detalhes:

```text
docs/DAILY_BRIEF_DELIVERY.md
docs/setup/GMAIL_DELIVERY_SETUP.md
```
