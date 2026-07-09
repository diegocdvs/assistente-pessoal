# ADR-008 - OAuth Microsoft Graph via MSAL token cache

Status: aceito  
Data: 2026-07-09

## Contexto

A Release 0.3B adiciona leitura real de e-mails Outlook pelo Microsoft Graph sem alterar o pipeline principal. O endpoint escolhido e `GET /me/messages`.

## Decisao

Usar Microsoft Entra ID com delegated OAuth e MSAL Python. A aplicacao le um `SerializableTokenCache` armazenado no Secret Manager e chama `acquire_token_silent()` para obter access tokens.

Somente `app/auth/microsoft.py` conhece MSAL. O `OutlookConnector` depende de uma abstracao `OAuthProvider` e de um cliente de mensagens.

Escopos:

```text
offline_access
https://graph.microsoft.com/Mail.Read
```

## Alternativas consideradas

- Client Credentials: rejeitado nesta release porque `/me/messages` exige contexto de usuario. App-only deve usar `/users/{id}/messages` e outra politica de consentimento.
- Refresh token manual: rejeitado porque MSAL ja implementa cache e renovacao segura.
- Secrets criados automaticamente pelo app: rejeitado para manter operacao explicita e auditavel.

## Consequencias

- Outlook pode ser ativado por feature flag sem mudar `DailyJob`.
- O dominio continua livre de detalhes Microsoft.
- O token cache precisa ser gerado fora do job e gravado no Secret Manager.
- A release nao executa acoes mutaveis.

## Impacto futuro

Quando Calendar ou automacoes forem adicionados, novos escopos e endpoints deverao passar por ADR propria. Esta decisao cobre apenas leitura read-only de e-mail Outlook.
