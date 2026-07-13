# ADR-015 - Daily Brief Delivery por Gmail separado do GmailConnector

## Status

Aceita

## Contexto

O `GmailConnector` do projeto e responsavel por leitura e normalizacao de mensagens. A Release 0.10 adiciona entrega do Daily Brief por e-mail, que e uma acao mutavel e possui escopos OAuth diferentes.

Misturar leitura de inbox e envio de relatorios no mesmo conector aumentaria o risco operacional e dificultaria auditoria.

## Decisao

Criar uma capability separada:

```text
DailyBrief
 -> Delivery Policy
 -> Email Renderer
 -> GmailDailyBriefDeliveryClient
 -> DeliveryRepository
```

O cliente `GmailDailyBriefDeliveryClient` nao le mensagens. Ele somente cria rascunhos ou envia mensagens quando a `DailyBriefDeliveryPolicy` permitir.

## Consequencias

- `GmailConnector` permanece inalterado funcionalmente.
- Delivery fica desligado por padrao.
- `send` exige `DAILY_BRIEF_DELIVERY_ALLOW_SEND=true`.
- Entregas sao idempotentes por `brief_id`, conta, destinatario e modo.
- O corpo do e-mail nao e persistido, apenas metadados e IDs do Gmail.

## Fora de escopo

- Scheduler.
- WhatsApp.
- Outlook delivery.
- Anexos.
- CC/BCC.
- Tracking.
- IA.
