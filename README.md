# Assistente Pessoal

Assistente pessoal executado como Cloud Run Job para ler caixas Gmail configuradas, classificar mensagens por regras e persistir o resultado no Firestore.

## Sprint 1

Implementado:

- AccountManager baseado em `config/accounts.yaml`.
- Suporte nativo a multiplas contas habilitadas.
- Gmail Connector com `google-api-python-client`, refresh token e Google Secret Manager.
- Leitura dos emails recentes sem marcar como lido e sem modificar a caixa.
- Persistencia de execucoes em `runs` e mensagens processadas em `processed_emails`.
- Classificador inicial por regras para seguranca, financeiro, eventos, trabalho, compras, newsletters, promocoes e outros.
- Testes unitarios para contas, classificador, Gmail, job e Firestore.

## Fluxo

```text
Cloud Run Job
  -> AccountManager
  -> GmailConnector
  -> Gmail
  -> Classifier
  -> Firestore
```

## Configuracao de contas

As contas ficam em `config/accounts.yaml`. Para adicionar uma nova conta Gmail, inclua uma entrada:

```yaml
accounts:
  - id: pessoal_google
    label: Pessoal
    provider: gmail
    email: pessoa@example.com
    enabled: true
    secret_prefix: google-pessoal
    max_emails: 10
    calendar:
      enabled: false
    firestore:
      enabled: true
    policies:
      dry_run: true
      mark_read_categories: []
      never_mark_read_priorities:
        - critica
        - importante
```

O codigo nao depende de nenhuma conta especifica. Os secrets sao resolvidos por `secret_prefix`:

```text
<secret_prefix>-client-secret-json
<secret_prefix>-refresh-token
```

## Gmail e seguranca

O conector Gmail usa `gmail.readonly` durante a execucao do job. Ele chama apenas endpoints de listagem/leitura (`messages.list` e `messages.get`), portanto:

- nunca marca emails como lidos;
- nunca arquiva;
- nunca apaga;
- nunca altera labels;
- nunca envia mensagens.

## Firestore

Colecoes usadas:

```text
runs/              resumo de cada execucao
processed_emails/  mensagem, classificacao e acoes observacionais
```

O ID de `processed_emails` combina `account_id`, `provider` e `message_id`, evitando duplicacao simples em reprocessamentos.

## Bootstrap Google local

No Windows, dentro do repositorio:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/google_oauth_local.py --client-secret-file client_secret.json --secret-prefix google-pessoal
```

Tambem e possivel salvar tokens com:

```bash
SECRET_PREFIX=google-pessoal GOOGLE_REFRESH_TOKEN=... scripts/save_google_tokens.sh
```

## Execucao local

```bash
pip install -r requirements.txt
PROJECT_ID=agenda-pessoal-projeto python -m app.main
```

Para usar outro arquivo de contas:

```bash
ACCOUNTS_CONFIG_PATH=config/accounts.yaml PROJECT_ID=agenda-pessoal-projeto python -m app.main
```

## Testes

```bash
python -m pytest
```

## Deploy

A infraestrutura existente usa Cloud Run Jobs. Os comandos atuais continuam no `Makefile`:

```bash
make deploy
make run-job
make list-jobs
```
