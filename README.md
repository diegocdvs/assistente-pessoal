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
- `app/core`: regras, classificador, rotina diária.
- `app/storage`: Firestore.
- `scripts/bootstrap_google.py`: fluxo local para gerar refresh token Google e salvar no Secret Manager.

## Variáveis principais

```bash
PROJECT_ID=agenda-pessoal-projeto
REGION=southamerica-east1
DRY_RUN=true
GOOGLE_CLIENT_SECRET_JSON=google-client-secret-json
GOOGLE_REFRESH_TOKEN=google-refresh-token
```

## Bootstrap Google local

Rode no seu Windows, dentro do repositório clonado:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/bootstrap_google.py --project-id agenda-pessoal-projeto --client-secret-file client_secret.json
```

O script abre o navegador, autoriza os escopos `gmail.modify` e `calendar.events`, gera o refresh token e grava os secrets no Secret Manager.

## Deploy manual inicial

```bash
gcloud config set project agenda-pessoal-projeto
gcloud config set run/region southamerica-east1
gcloud builds submit --tag southamerica-east1-docker.pkg.dev/agenda-pessoal-projeto/assistente-pessoal/app:latest
gcloud run jobs create assistente-pessoal-diario \
  --image southamerica-east1-docker.pkg.dev/agenda-pessoal-projeto/assistente-pessoal/app:latest \
  --region southamerica-east1 \
  --service-account assistente-pessoal-runner@agenda-pessoal-projeto.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=agenda-pessoal-projeto,DRY_RUN=true
```

## Scheduler

Será criado depois do primeiro deploy validado.
