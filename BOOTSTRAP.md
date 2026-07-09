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
