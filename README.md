# Assistente Pessoal

Projeto para rotina diária de triagem de Gmail/Outlook, criação segura de eventos na Google Agenda, histórico no Firestore e envio futuro de relatório por WhatsApp.

## Estado atual

MVP em **modo seguro** (`DRY_RUN=true`). Nesta fase o sistema lê/classifica/simula ações, mas não marca e-mails como lidos nem cria eventos.

## Arquitetura

```text
Cloud Scheduler -> Cloud Run Job -> Gmail / Outlook / Calendar / Firestore / WhatsApp
```

Camadas:

- `app/connectors`: Gmail, Outlook, Google Calendar, WhatsApp.
- `app/core`: regras, classificador, contas e rotina diária.
- `app/storage`: Firestore.
- `scripts/google_oauth_local.py`: fluxo local para gerar refresh token Google.

## Nomes padronizados para a conta Google pessoal

A primeira conta Google usa estes nomes:

```text
google-pessoal-client-secret-json
google-pessoal-refresh-token
```

Para uma futura conta profissional, manteremos o mesmo padrão:

```text
google-profissional-client-secret-json
google-profissional-refresh-token
```

Assim o sistema pode tratar múltiplos Gmails sem alterar código estrutural.

## Bootstrap Google local

Rode no Windows, dentro do repositório clonado:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/google_oauth_local.py --client-secret-file client_secret.json
```

O script abre o navegador, autoriza os escopos `gmail.modify` e `calendar.events`, gera o refresh token e pode salvar no Secret Manager.

## Deploy manual inicial

O projeto usa **Cloud Run Jobs**, não Cloud Run Services. Portanto os comandos corretos usam `gcloud run jobs`.

```bash
gcloud config set project agenda-pessoal-projeto
gcloud config set run/region southamerica-east1
gcloud artifacts repositories create assistente-pessoal --repository-format=docker --location=southamerica-east1 2>/dev/null || true
gcloud builds submit --tag southamerica-east1-docker.pkg.dev/agenda-pessoal-projeto/assistente-pessoal/app:latest
gcloud run jobs create assistente-pessoal-diario \
  --image southamerica-east1-docker.pkg.dev/agenda-pessoal-projeto/assistente-pessoal/app:latest \
  --region southamerica-east1 \
  --service-account assistente-pessoal-runner@agenda-pessoal-projeto.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=agenda-pessoal-projeto,REGION=southamerica-east1,DRY_RUN=true,GOOGLE_CLIENT_SECRET_NAME=google-pessoal-client-secret-json,GOOGLE_REFRESH_TOKEN_NAME=google-pessoal-refresh-token
```

Se o job já existir, use `gcloud run jobs update` com os mesmos parâmetros.

## Comandos úteis

```bash
make deploy
make run-job
make list-jobs
```

## Scheduler

Será criado depois do primeiro deploy validado.
