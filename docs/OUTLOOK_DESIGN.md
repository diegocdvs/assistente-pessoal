# Outlook Design - Release 0.3B

Status: integracao Microsoft Graph read-only atras de feature flag
Provider: `outlook`

## Objetivo

Adicionar Outlook como segundo provedor real de e-mail sem alterar o pipeline principal e sem exigir infraestrutura nova.

Fluxo:

```text
Microsoft Graph /me/messages
        |
        v
OutlookConnector
        |
        v
OutlookNormalizer
        |
        v
EmailEntity
        |
        v
WorkItem
        |
        v
Classifier -> Persistence -> AutomationPlanner -> Report
```

## Contratos

Todos os conectores implementam:

```python
provider: str
fetch_recent(account) -> list[EmailEntity]
```

`OutlookConnector` nao conhece MSAL. Ele depende de:

- `OAuthProvider`: entrega access token.
- `OutlookMessageClient`: le mensagens normalizadas do provider externo.
- `OutlookNormalizer`: converte payload Graph em `EmailEntity`.

## OAuth

O fluxo escolhido e Authorization Code Flow com Microsoft Entra ID para gerar token cache inicial, seguido por `acquire_token_silent()` do MSAL no runtime.

Motivo: `GET /me/messages` e delegated/user context. Client Credentials e app-only e nao representa `/me`.

Escopos:

```text
offline_access
https://graph.microsoft.com/Mail.Read
```

## Secrets

Para `secret_prefix: outlook-profissional`:

```text
outlook-profissional-tenant-id
outlook-profissional-client-id
outlook-profissional-client-secret
outlook-profissional-token-cache
```

O app apenas le secrets existentes.

## Graph client

Endpoint:

```text
GET https://graph.microsoft.com/v1.0/me/messages
```

Campos selecionados:

```text
id, conversationId, changeKey, internetMessageId, subject, bodyPreview,
receivedDateTime, importance, isRead, webLink, categories, from,
toRecipients, ccRecipients, internetMessageHeaders
```

## Normalizacao

```text
Graph id                  -> EmailEntity.id
conversationId            -> EmailEntity.thread_id
subject                   -> EmailEntity.subject
from.emailAddress         -> EmailEntity.sender
toRecipients/ccRecipients -> EmailEntity.recipients
bodyPreview               -> EmailEntity.snippet
categories                -> EmailEntity.labels
receivedDateTime          -> EmailEntity.received_at
internetMessageHeaders    -> EmailEntity.raw_headers
importance/isRead/etc.    -> EmailEntity.metadata
```

## Feature flag

```text
OUTLOOK_ENABLED=false
```

Esse e o padrao. Quando falso, `ConnectorManager` registra Outlook desabilitado e `fetch_recent()` retorna lista vazia.

Quando verdadeiro, `ConnectorManager` injeta:

- `MicrosoftOAuthProvider`
- `MicrosoftGraphMailClient`
- `OutlookConnector(enabled=True)`

## Limites

Nao implementado:

- envio;
- mover, arquivar, excluir;
- marcar como lido;
- anexos;
- Calendar;
- WhatsApp;
- IA;
- automacoes reais.

Outlook continua read-only e passa pelo mesmo `DRY_RUN` operacional do projeto.
