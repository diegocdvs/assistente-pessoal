# Outlook Design - Release 0.3A

Status: foundation stub  
Escopo: preparar arquitetura para Outlook sem Microsoft Graph real  
Provider: `outlook`

## Objetivo

A Release 0.3A prepara o Assistente Pessoal para suportar Outlook como segundo provedor de e-mail, sem exigir Azure, credenciais Microsoft ou chamadas reais ao Microsoft Graph.

O objetivo e validar contratos:

```text
Microsoft Graph payload fake
        |
        v
OutlookNormalizer
        |
        v
EmailEntity
        |
        v
WorkItem
```

## Arquitetura

Arquivos principais:

```text
app/connectors/base.py
app/connectors/outlook.py
app/connectors/manager.py
tests/test_outlook_connector.py
```

`app/connectors/base.py` define a interface comum:

```python
class Connector(Protocol):
    provider: str

    def fetch_recent(self, account) -> list[EmailEntity]:
        ...
```

`OutlookConnector` implementa essa interface, mas permanece em modo stub.

## Comportamento atual

Por padrao:

```text
OUTLOOK_ENABLED=false
```

E:

```python
OutlookConnector(enabled=False)
```

Nesse estado, `fetch_recent()` retorna lista vazia e nao faz chamadas externas.

Nao ha:

- OAuth Microsoft;
- Graph client real;
- chamadas HTTP;
- Azure app registration obrigatoria;
- leitura real de mailbox;
- mutacao de e-mails;
- automacao.

## Normalizacao

O `OutlookNormalizer` converte payloads fake compatíveis com Microsoft Graph para `EmailEntity`.

Campos Graph usados:

```text
id
conversationId
subject
from.emailAddress
toRecipients
ccRecipients
bodyPreview
categories
receivedDateTime
internetMessageHeaders
importance
isRead
webLink
internetMessageId
changeKey
```

Mapeamento:

```text
Graph id                 -> EmailEntity.id
conversationId           -> EmailEntity.thread_id
subject                  -> EmailEntity.subject
from.emailAddress        -> EmailEntity.sender
toRecipients/ccRecipients -> EmailEntity.recipients
bodyPreview              -> EmailEntity.snippet
categories               -> EmailEntity.labels
receivedDateTime         -> EmailEntity.received_at
internetMessageHeaders   -> EmailEntity.raw_headers
importance/isRead/etc.   -> EmailEntity.metadata
```

Depois disso, `EmailEntity.to_work_item()` gera:

```text
source=outlook
type=email
payload=EmailEntity.to_dict()
```

## OAuth esperado futuramente

A integracao real deve usar Microsoft Entra ID e Microsoft Graph.

Escopos esperados inicialmente:

```text
Mail.Read
offline_access
```

Escopos mutaveis, como `Mail.ReadWrite`, nao devem ser usados enquanto nao existir uma decisao explicita de automacao e seguranca.

## Secrets esperados futuramente

Para uma conta com:

```yaml
secret_prefix: outlook-profissional
```

Secrets provaveis:

```text
outlook-profissional-tenant-id
outlook-profissional-client-id
outlook-profissional-client-secret
outlook-profissional-refresh-token
```

Esses secrets ainda nao sao lidos na Release 0.3A.

## Endpoints esperados futuramente

Leitura inicial:

```text
GET https://graph.microsoft.com/v1.0/me/messages
```

Parametros provaveis:

```text
$top
$select=id,conversationId,subject,from,toRecipients,ccRecipients,bodyPreview,categories,receivedDateTime,internetMessageHeaders,importance,isRead,webLink,internetMessageId,changeKey
$orderby=receivedDateTime desc
```

## Fluxo futuro

```text
AccountManager
        |
        v
ConnectorManager
        |
        v
OutlookConnector
        |
        v
Microsoft Graph
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
Classifier
        |
        v
Persistence
        |
        v
AutomationPlanner
        |
        v
Report
```

## Limitacoes da Release 0.3A

- Outlook nao processa contas reais.
- `OutlookConnector` nao autentica.
- `OutlookConnector` nao chama Microsoft Graph.
- `OUTLOOK_ENABLED` permanece desligado por padrao.
- `ConnectorManager` reconhece `outlook`, mas o stub desabilitado retorna lista vazia.
- Testes usam payloads fake do Graph.

## Criterios de seguranca

Enquanto nao houver release especifica de integracao real:

- nao adicionar credenciais Azure;
- nao alterar IAM/GCP;
- nao alterar OAuth Google;
- nao executar automacoes;
- nao marcar e-mails como lidos;
- nao mover, arquivar ou excluir mensagens.
