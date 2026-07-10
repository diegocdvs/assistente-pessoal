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
