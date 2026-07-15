# Scheduled Daily Brief GCP Setup

Status: operacional, modo draft primeiro

## Pre-requisitos

- Release 0.10 validada.
- Cloud Run Job principal funcionando.
- Firestore habilitado.
- Secret Manager com secrets Google.
- Refresh token com escopo de draft:

```text
https://www.googleapis.com/auth/gmail.compose
```

Para envio real posterior:

```text
https://www.googleapis.com/auth/gmail.send
```

## Variaveis iniciais em draft

```bash
PROJECT_ID=agenda-pessoal-projeto
REGION=southamerica-east1
JOB_NAME=assistente-pessoal-daily-brief
IMAGE=southamerica-east1-docker.pkg.dev/${PROJECT_ID}/assistente-pessoal/app:latest
SERVICE_ACCOUNT=assistente-pessoal-runner@${PROJECT_ID}.iam.gserviceaccount.com
RECIPIENT=destinatario@example.com
```

## Criar ou atualizar Cloud Run Job

O job reutiliza o mesmo container e muda apenas o comando.

```bash
gcloud run jobs create ${JOB_NAME} \
  --project ${PROJECT_ID} \
  --region ${REGION} \
  --image ${IMAGE} \
  --service-account ${SERVICE_ACCOUNT} \
  --command python \
  --args scripts/scheduled_daily_brief.py,--trigger,scheduler \
  --set-env-vars PROJECT_ID=${PROJECT_ID},REGION=${REGION},DRY_RUN=true,DAILY_BRIEF_SCHEDULE_ENABLED=true,DAILY_BRIEF_SCHEDULE_MODE=draft,DAILY_BRIEF_SCHEDULE_TIME=07:30,DAILY_BRIEF_SCHEDULE_TIMEZONE=America/Sao_Paulo,DAILY_BRIEF_SCHEDULE_RECIPIENTS=${RECIPIENT},DAILY_BRIEF_DELIVERY_ENABLED=true,DAILY_BRIEF_DELIVERY_MODE=draft,DAILY_BRIEF_DELIVERY_RECIPIENTS=${RECIPIENT},DAILY_BRIEF_DELIVERY_ALLOW_SEND=false
```

Se o job ja existir:

```bash
gcloud run jobs update ${JOB_NAME} \
  --project ${PROJECT_ID} \
  --region ${REGION} \
  --image ${IMAGE} \
  --service-account ${SERVICE_ACCOUNT} \
  --command python \
  --args scripts/scheduled_daily_brief.py,--trigger,scheduler \
  --set-env-vars PROJECT_ID=${PROJECT_ID},REGION=${REGION},DRY_RUN=true,DAILY_BRIEF_SCHEDULE_ENABLED=true,DAILY_BRIEF_SCHEDULE_MODE=draft,DAILY_BRIEF_SCHEDULE_TIME=07:30,DAILY_BRIEF_SCHEDULE_TIMEZONE=America/Sao_Paulo,DAILY_BRIEF_SCHEDULE_RECIPIENTS=${RECIPIENT},DAILY_BRIEF_DELIVERY_ENABLED=true,DAILY_BRIEF_DELIVERY_MODE=draft,DAILY_BRIEF_DELIVERY_RECIPIENTS=${RECIPIENT},DAILY_BRIEF_DELIVERY_ALLOW_SEND=false
```

## IAM minimo

Runtime do job:

```bash
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:${SERVICE_ACCOUNT} \
  --role roles/secretmanager.secretAccessor

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:${SERVICE_ACCOUNT} \
  --role roles/datastore.user
```

Service Account do Scheduler para invocar Run Jobs:

```bash
SCHEDULER_SA=assistente-pessoal-scheduler@${PROJECT_ID}.iam.gserviceaccount.com

gcloud iam service-accounts create assistente-pessoal-scheduler \
  --project ${PROJECT_ID}

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:${SCHEDULER_SA} \
  --role roles/run.developer

gcloud iam service-accounts add-iam-policy-binding ${SERVICE_ACCOUNT} \
  --member serviceAccount:${SCHEDULER_SA} \
  --role roles/iam.serviceAccountUser \
  --project ${PROJECT_ID}
```

Nao conceder Owner ou Editor.

## Criar Cloud Scheduler

```bash
gcloud scheduler jobs create http assistente-pessoal-daily-brief \
  --project ${PROJECT_ID} \
  --location ${REGION} \
  --schedule "30 7 * * *" \
  --time-zone "America/Sao_Paulo" \
  --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
  --http-method POST \
  --oauth-service-account-email ${SCHEDULER_SA} \
  --max-retry-attempts 3 \
  --min-backoff 60s \
  --max-backoff 300s
```

## Execucao manual

```bash
gcloud run jobs execute ${JOB_NAME} --project ${PROJECT_ID} --region ${REGION} --wait
```

## Validacao segura

```bash
make validate
make scheduled-daily-brief-dry-run
make scheduled-daily-brief-status
make daily-brief
make daily-brief-json
make daily-brief-draft
make calendar
make subscriptions
make double-check
make release
```

Nao executar envio real na validacao padrao.

## Promover para send posteriormente

Somente depois de validar draft:

1. Regerar refresh token com `--include-gmail-send`.
2. Confirmar destinatario na allowlist.
3. Atualizar job:

```bash
gcloud run jobs update ${JOB_NAME} \
  --project ${PROJECT_ID} \
  --region ${REGION} \
  --set-env-vars DAILY_BRIEF_SCHEDULE_MODE=send,DAILY_BRIEF_DELIVERY_MODE=send,DAILY_BRIEF_DELIVERY_ALLOW_SEND=true,DRY_RUN=false
```

Nao ha promocao automatica de draft para send.

## Pausa emergencial

```bash
gcloud scheduler jobs pause assistente-pessoal-daily-brief --project ${PROJECT_ID} --location ${REGION}
gcloud run jobs update ${JOB_NAME} --project ${PROJECT_ID} --region ${REGION} --set-env-vars DAILY_BRIEF_SCHEDULE_ENABLED=false
```

## Rollback

```bash
gcloud scheduler jobs pause assistente-pessoal-daily-brief --project ${PROJECT_ID} --location ${REGION}
gcloud run jobs update ${JOB_NAME} --project ${PROJECT_ID} --region ${REGION} --image IMAGEM_ANTERIOR
```

## Troubleshooting

- `recipient_outside_allowlist`: alinhar `DAILY_BRIEF_SCHEDULE_RECIPIENTS` e `DAILY_BRIEF_DELIVERY_RECIPIENTS`.
- `blocked_by_policy`: conferir modo, allowlist e `DAILY_BRIEF_DELIVERY_ALLOW_SEND`.
- `delivery_uncertain`: nao reenviar; verificar Gmail e Firestore manualmente.
- `missing_credentials`: revisar secrets e permissao `roles/secretmanager.secretAccessor`.
- `insufficient_oauth_scope`: regenerar refresh token com escopo correto.
