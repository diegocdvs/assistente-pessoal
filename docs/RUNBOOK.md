# Runbook Operacional — Assistente Pessoal

## 1. Ambiente padrão

Executar sempre pelo Cloud Shell.

```bash
cd ~/assistente-pessoal
source .venv/bin/activate || true
```

## 2. Atualizar código

```bash
git checkout main
git pull
```

## 3. Validar localmente

```bash
python -m pytest
python -m compileall app scripts
```

## 4. Deploy

```bash
make deploy
```

## 5. Executar job

```bash
make run-job
```

## 6. Ler logs

Após o `make run-job`, copiar o nome da execução e rodar:

```bash
gcloud beta run jobs executions logs read NOME_DA_EXECUCAO --region southamerica-east1
```

## 7. Validar Firestore

```bash
python - <<'PY'
from google.cloud import firestore

PROJECT_ID = "agenda-pessoal-projeto"
ACCOUNT_ID = "pessoal_google"

db = firestore.Client(project=PROJECT_ID)
for sub in ["emails", "classifications", "action_plans"]:
    docs = list(db.collection("accounts").document(ACCOUNT_ID).collection(sub).limit(5).stream())
    print(sub, len(docs))
    for doc in docs:
        print(" -", doc.id)
PY
```

## 8. Checklist de sucesso

- Cloud Build termina com `STATUS: SUCCESS`.
- Cloud Run Job termina com `successfully completed`.
- Logs mostram `Gmail retornou 10 mensagens` ou contagem configurada.
- `errors` no report está vazio.
- Firestore mostra documentos em `emails` e `classifications`.
- `DRY_RUN=true` nos logs.

## 9. Erros conhecidos

### `invalid_scope`

Causa: escopos do `GmailConnector` diferentes dos usados para gerar o refresh token.

Solução atual:

```python
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
]
```

### `accessNotConfigured`

Causa: API não habilitada no projeto.

Solução:

```bash
gcloud services enable gmail.googleapis.com
```

### `No module named pytest`

Causa: venv não ativada ou dependências não instaladas.

Solução:

```bash
cd ~/assistente-pessoal
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### `make: No rule to make target 'make'`

Causa: comando incorreto `make deploy make run-job`.

Solução:

```bash
make deploy
make run-job
```

### `--region: command not found`

Causa: quebra incorreta de linha no shell.

Solução: executar em linha única.

```bash
gcloud beta run jobs executions logs read NOME --region southamerica-east1
```

## 10. Regra operacional

Não diagnosticar manualmente por muito tempo. Se um erro ocorrer duas vezes, criar verificação em `make doctor` ou `make smoke`.
