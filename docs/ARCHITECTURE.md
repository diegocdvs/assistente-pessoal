# Arquitetura do Assistente Pessoal

## Objetivo

Executar uma rotina diaria no Google Cloud para ler emails de multiplas contas, classificar mensagens por regras explicitas e persistir historico no Firestore.

## Fluxo Sprint 1

```text
Cloud Run Job
  -> app.main
  -> DailyJob
  -> AccountManager
  -> GmailConnector
  -> Gmail API
  -> Rule Classifier
  -> FirestoreStore
```

## Componentes

### AccountManager

`app/core/accounts.py` carrega `config/accounts.yaml`, valida a estrutura e entrega apenas contas habilitadas para o job. Uma nova conta deve exigir somente uma nova entrada YAML, sem alteracao de codigo.

### GmailConnector

`app/connectors/gmail.py` usa:

- `google-api-python-client`;
- refresh token;
- Google Secret Manager;
- secrets derivados de `secret_prefix`.

Durante a execucao, o conector usa escopo `gmail.readonly` e chama somente `messages.list` e `messages.get`.

### Classifier

`app/core/classifier.py` aplica regras deterministicas iniciais:

- seguranca: prioridade critica;
- financeiro, evento e trabalho: prioridade importante;
- compra e outros: prioridade informativa;
- newsletter e promocoes: ruido.

O classificador pode indicar possivel evento, mas a Sprint 1 apenas registra essa informacao.

### FirestoreStore

`app/storage/firestore_store.py` persiste:

- `runs`: resumo da execucao;
- `processed_emails`: mensagem, classificacao, conta, provedor e acoes observacionais.

## Multi-contas

Cada conta contem:

- `id`;
- `label`;
- `provider`;
- `email`;
- `enabled`;
- `secret_prefix`;
- `max_emails`;
- `calendar.enabled`;
- `firestore.enabled`;
- `policies`.

Providers planejados:

- `gmail`: implementado na Sprint 1;
- `outlook`: reservado para sprint futura;
- Google Calendar, WhatsApp e IA: preparados no desenho, sem execucao mutavel nesta sprint.

## Politica de seguranca

A Sprint 1 e somente leitura para email:

- nao marca como lido;
- nao arquiva;
- nao apaga;
- nao altera labels;
- nao envia email;
- nao cria eventos.

Acoes retornadas no relatorio sao observacionais, por exemplo destacar alerta critico ou registrar possivel evento para revisao futura.
