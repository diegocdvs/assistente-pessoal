# Azure Setup - Outlook / Microsoft Graph

Status: documentacao para Release 0.3B  
Escopo: preparar credenciais para leitura read-only de Outlook via Microsoft Graph.

## Fluxo OAuth escolhido

O Cloud Run Job le `GET /me/messages`, que representa a caixa do usuario autenticado. Por isso, o fluxo correto e delegated OAuth com Microsoft Entra ID, usando Authorization Code Flow para gerar um token cache inicial e MSAL para renovar access tokens de forma silenciosa.

Escopos esperados:

```text
offline_access
https://graph.microsoft.com/Mail.Read
```

Nao usar Client Credentials nesta release: esse fluxo e app-only, nao representa `/me` e normalmente exigiria `/users/{id}/messages` com consentimento de aplicacao.

## App Registration

No Microsoft Entra ID:

1. Criar uma App Registration.
2. Criar um client secret.
3. Configurar redirect URI para o bootstrap local de Authorization Code Flow.
4. Conceder permissao delegated `Mail.Read`.
5. Garantir que `offline_access` seja solicitado no bootstrap.

## Secrets

Para uma conta em `config/accounts.yaml`:

```yaml
accounts:
  - id: profissional_outlook
    provider: outlook
    email: pessoa@empresa.com
    enabled: false
    secret_prefix: outlook-profissional
```

Secrets esperados no Secret Manager:

```text
outlook-profissional-tenant-id
outlook-profissional-client-id
outlook-profissional-client-secret
outlook-profissional-token-cache
```

O projeto nao cria secrets automaticamente.

## Token cache

`outlook-profissional-token-cache` deve conter o cache serializado do MSAL (`SerializableTokenCache`). A aplicacao le esse cache, chama `acquire_token_silent()` e deixa o MSAL gerenciar renovacao de access token a partir dos dados existentes no cache.

Esta release nao persiste atualizacoes do cache de volta no Secret Manager. Se a conta perder consentimento ou o cache expirar completamente, gere novo cache via bootstrap e atualize o secret manualmente.

## Endpoint

Leitura implementada:

```text
GET https://graph.microsoft.com/v1.0/me/messages
```

Parametros:

```text
$top=<max_emails>
$orderby=receivedDateTime desc
$select=id,conversationId,changeKey,internetMessageId,subject,bodyPreview,receivedDateTime,importance,isRead,webLink,categories,from,toRecipients,ccRecipients,internetMessageHeaders
```

## Limites de seguranca

Nao implementado nesta release:

- envio de e-mail;
- mover, arquivar ou excluir mensagens;
- marcar como lido;
- anexos;
- Calendar;
- WhatsApp;
- IA;
- automacoes reais.

`OUTLOOK_ENABLED=false` permanece o padrao operacional.
