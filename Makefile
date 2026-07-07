PROJECT_ID ?= agenda-pessoal-projeto
REGION ?= southamerica-east1
IMAGE ?= $(REGION)-docker.pkg.dev/$(PROJECT_ID)/assistente-pessoal/app:latest
JOB_NAME ?= assistente-pessoal-diario

.PHONY: install google-token deploy run-job

install:
	python -m pip install -r requirements.txt

google-token:
	python scripts/google_oauth_local.py --client-secret-file client_secret.json

deploy:
	gcloud config set project $(PROJECT_ID)
	gcloud artifacts repositories create assistente-pessoal --repository-format=docker --location=$(REGION) 2>/dev/null || true
	gcloud builds submit --tag $(IMAGE)
	gcloud run jobs create $(JOB_NAME) --image $(IMAGE) --region $(REGION) --set-env-vars PROJECT_ID=$(PROJECT_ID),REGION=$(REGION),DRY_RUN=true 2>/dev/null || gcloud run jobs update $(JOB_NAME) --image $(IMAGE) --region $(REGION) --set-env-vars PROJECT_ID=$(PROJECT_ID),REGION=$(REGION),DRY_RUN=true

run-job:
	gcloud run jobs execute $(JOB_NAME) --region $(REGION) --wait
