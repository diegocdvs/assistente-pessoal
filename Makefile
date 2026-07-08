PROJECT_ID ?= agenda-pessoal-projeto
REGION ?= southamerica-east1
IMAGE ?= $(REGION)-docker.pkg.dev/$(PROJECT_ID)/assistente-pessoal/app:latest
JOB_NAME ?= assistente-pessoal-diario
SERVICE_ACCOUNT ?= assistente-pessoal-runner@$(PROJECT_ID).iam.gserviceaccount.com

.PHONY: install google-token validate doctor smoke release deploy run-job list-jobs

install:
	python -m pip install -r requirements.txt

google-token:
	python scripts/google_oauth_local.py --client-secret-file client_secret.json

validate:
	python -m pytest
	python -m compileall app scripts

doctor:
	python scripts/doctor.py --project-id $(PROJECT_ID) --region $(REGION) --job-name $(JOB_NAME)

smoke:
	python scripts/smoke.py --project-id $(PROJECT_ID) --region $(REGION) --job-name $(JOB_NAME)

release: validate doctor deploy smoke

deploy:
	gcloud config set project $(PROJECT_ID)
	gcloud artifacts repositories create assistente-pessoal --repository-format=docker --location=$(REGION) 2>/dev/null || true
	gcloud builds submit --tag $(IMAGE)
	gcloud run jobs create $(JOB_NAME) --image $(IMAGE) --region $(REGION) --service-account $(SERVICE_ACCOUNT) --set-env-vars PROJECT_ID=$(PROJECT_ID),REGION=$(REGION),DRY_RUN=true,GOOGLE_CLIENT_SECRET_NAME=google-pessoal-client-secret-json,GOOGLE_REFRESH_TOKEN_NAME=google-pessoal-refresh-token 2>/dev/null || gcloud run jobs update $(JOB_NAME) --image $(IMAGE) --region $(REGION) --service-account $(SERVICE_ACCOUNT) --set-env-vars PROJECT_ID=$(PROJECT_ID),REGION=$(REGION),DRY_RUN=true,GOOGLE_CLIENT_SECRET_NAME=google-pessoal-client-secret-json,GOOGLE_REFRESH_TOKEN_NAME=google-pessoal-refresh-token

run-job:
	gcloud run jobs execute $(JOB_NAME) --region $(REGION) --wait

list-jobs:
	gcloud run jobs list --region $(REGION)
