# Runbook Operacional - Assistente Pessoal

## 1. Ambiente padrao

Executar preferencialmente pelo Cloud Shell.

```bash
cd ~/assistente-pessoal
source .venv/bin/activate || true
```

## 2. Atualizar codigo

```bash
git checkout main
git pull
```

## 3. Validar localmente

```bash
make validate
```

O alvo executa:

```bash
python -m pytest
python -m compileall app scripts
```

## 4. Diagnostico

```bash
make doctor
```

Valida Python, pip, `.venv`, Docker, gcloud, autenticacao, projeto ativo, regiao, APIs, secrets e Cloud Run Job.

## 5. Deploy

```bash
make deploy
```

## 6. Smoke test

```bash
make smoke
```

O smoke executa o job, captura o nome da execucao, le logs para detectar erros conhecidos e validar sinais basicos. Se o JSON completo do report estiver truncado ou ausente nos logs, faz fallback para Firestore.

Falhas do smoke:

- job falhou;
- erro conhecido nos logs: `invalid_scope`, `accessNotConfigured`, `RefreshError`, `HttpError 403`, `MVP placeholder ativo`;
- `report.errors != []`, quando o report JSON estiver disponivel;
- Firestore sem documentos em `accounts/pessoal_google/emails`;
- Firestore sem documentos em `accounts/pessoal_google/classifications`.

`action_plans` vazio gera `WARN`, nao falha.

## 7. Release completo

```bash
make release
```

O alvo executa, em ordem:

```text
make validate
make doctor
make deploy
make smoke
```

O `make` interrompe o fluxo na primeira etapa que falhar.

## 8. Ler logs manualmente

Quando necessario, copie o nome da execucao mostrado pelo smoke e rode:

```bash
gcloud beta run jobs executions logs read NOME_DA_EXECUCAO --region southamerica-east1
```

## 9. Validar Firestore manualmente

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

## 10. Checklist de sucesso

- Cloud Build termina com `STATUS: SUCCESS`.
- Cloud Run Job termina com sucesso.
- Logs mostram `Gmail retornou 10 mensagens` ou contagem configurada.
- `errors` no report esta vazio quando o JSON completo aparecer nos logs.
- Firestore mostra documentos em `emails` e `classifications`.
- `action_plans` vazio aparece como `WARN`.
- `DRY_RUN=true` permanece ativo.

## 11. Erros conhecidos

### `invalid_scope`

Causa: escopos do `GmailConnector` diferentes dos usados para gerar o refresh token.

Solucao atual: manter os escopos usados para emitir o refresh token de producao ate que o token seja rotacionado.

```python
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
]
```

Mesmo com esses escopos, o codigo atual nao executa mutacoes: nao marca lido, nao move, nao exclui e nao cria eventos.

### `accessNotConfigured`

Causa: API nao habilitada no projeto.

Solucao:

```bash
gcloud services enable gmail.googleapis.com
```

### `No module named pytest`

Causa: venv nao ativada ou dependencias nao instaladas.

Solucao:

```bash
cd ~/assistente-pessoal
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### `make: No rule to make target 'make'`

Causa: comando incorreto `make deploy make run-job`.

Solucao:

```bash
make release
```

ou, manualmente:

```bash
make deploy
make smoke
```

### `--region: command not found`

Causa: quebra incorreta de linha no shell.

Solucao: executar em linha unica.

```bash
gcloud beta run jobs executions logs read NOME --region southamerica-east1
```

## 12. Regra operacional

Nao diagnosticar manualmente por muito tempo. Se um erro ocorrer duas vezes, criar verificacao em `make doctor` ou `make smoke`.
