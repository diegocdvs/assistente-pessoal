# Próximos passos

## 1. Atualizar o repositório local

No Windows, dentro da pasta do projeto:

```cmd
git pull
```

## 2. Instalar dependências

```cmd
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Gerar refresh token Google localmente

Coloque o arquivo OAuth baixado do Google Cloud na raiz do projeto com o nome:

```text
client_secret.json
```

Depois rode:

```cmd
python scripts/google_oauth_local.py --client-secret-file client_secret.json
```

Copie o `GOOGLE_REFRESH_TOKEN` gerado, sem enviar em chats.

## 4. Salvar secrets no Google Secret Manager

No Windows, com Google Cloud CLI autenticado e apontando para o projeto:

```cmd
gcloud config set project agenda-pessoal-projeto
```

Salve o JSON do client:

```cmd
gcloud secrets create google-pessoal-client-secret-json --data-file=client_secret.json
```

Salve o refresh token em arquivo temporário:

```cmd
echo COLE_O_REFRESH_TOKEN_AQUI> refresh_token.txt
gcloud secrets create google-pessoal-refresh-token --data-file=refresh_token.txt
del refresh_token.txt
```

## 5. Deploy inicial

```cmd
make deploy
```

Se `make` não estiver disponível no Windows, usaremos os comandos `gcloud` equivalentes.

## 6. Teste manual do job

```cmd
make run-job
```

## 7. Depois

- Ligar Gmail real no conector.
- Criar app Microsoft Entra para Outlook.
- Configurar WhatsApp Cloud API.
- Criar Scheduler diário.
