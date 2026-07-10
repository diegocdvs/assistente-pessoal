PROJECT_ID ?= agenda-pessoal-projeto
REGION ?= southamerica-east1
IMAGE ?= $(REGION)-docker.pkg.dev/$(PROJECT_ID)/assistente-pessoal/app:latest
JOB_NAME ?= assistente-pessoal-diario
SERVICE_ACCOUNT ?= assistente-pessoal-runner@$(PROJECT_ID).iam.gserviceaccount.com
PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; elif [ -x .venv/Scripts/python.exe ]; then echo .venv/Scripts/python.exe; else echo python; fi)

.PHONY: install google-token check-python-deps validate doctor smoke subscriptions double-check release deploy run-job list-jobs

install:
	$(PYTHON) -m pip install -r requirements.txt

google-token:
	$(PYTHON) scripts/google_oauth_local.py --client-secret-file client_secret.json

check-python-deps:
	$(PYTHON) -c "import pytest" || (echo "pytest nao encontrado. Execute '$(PYTHON) -m pip install -r requirements.txt' ou ative a .venv correta."; exit 1)

validate: check-python-deps
	$(PYTHON) -m pytest
	$(PYTHON) -m compileall app scripts

doctor:
	$(PYTHON) scripts/doctor.py --project-id $(PROJECT_ID) --region $(REGION) --job-name $(JOB_NAME)

smoke:
	$(PYTHON) scripts/smoke.py --project-id $(PROJECT_ID) --region $(REGION) --job-name $(JOB_NAME)

subscriptions:
	$(PYTHON) scripts/subscriptions.py --project-id $(PROJECT_ID) --summary --dry-run

double-check:
	$(PYTHON) scripts/double_check.py --project-id $(PROJECT_ID)

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
