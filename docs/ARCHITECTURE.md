# Arquitetura do Assistente Pessoal

## Pipeline consolidado

```text
Connector
  -> EmailEntity
  -> Classifier
  -> Persistence
  -> Automation
  -> Report
```

O objetivo da refatoracao e manter o dominio independente de APIs externas antes da entrada de Calendar, Outlook, WhatsApp ou IA.

## Contratos

### Connector

Conectores ficam em `app/connectors`. Eles leem provedores externos e retornam dados normalizados.

O `GmailConnector`:

- usa Secret Manager e refresh token;
- usa `gmail.readonly`;
- chama apenas endpoints de leitura;
- converte payloads Gmail para `EmailEntity`;
- guarda dados especificos do Gmail em `metadata`.

### EmailEntity

`app/core/models.py` define a entidade interna do pipeline:

```text
id, provider, account_id, account_email, thread_id, subject, sender,
recipients, snippet, labels, received_at, raw_headers, metadata
```

Camadas de dominio nao dependem de payloads Gmail.

### Classifier

`app/core/classifier.py` contem o `RuleBasedClassifier`.

Saida:

- `category`;
- `priority`;
- `reason`;
- `confidence`.

Categorias suportadas:

```text
financeiro, compra, entrega, evento, trabalho, seguranca, promocao,
newsletter, social, educacao, viagem, saude, outros
```

Prioridades suportadas:

```text
critica, alta, normal, baixa, ruido
```

### Persistence

`app/storage/persistence.py` implementa `FirestorePersistence`.

Estrutura:

```text
runs/
accounts/<account_id>/emails/<message_id>
```

O metodo `upsert_email` faz merge para evitar duplicacao. Emails existentes recebem novo `last_seen_at`; emails novos tambem recebem `first_seen_at`.

### Automation

`app/core/automation.py` cria `ActionPlan` sem executar nada.

Formato:

```text
type, reason, dry_run, status
```

Por enquanto todas as acoes ficam planejadas e com `dry_run=true`.

### Report

`app/core/report.py` monta o relatorio final:

- total por conta;
- total por categoria;
- total por prioridade;
- erros;
- acoes planejadas;
- tempo de execucao.

## Orquestracao

`DailyJob` coordena:

1. Carregar contas habilitadas.
2. Buscar emails por conector.
3. Classificar `EmailEntity`.
4. Planejar automacoes.
5. Persistir email/classificacao/acoes.
6. Gerar e persistir relatorio do run.

## Politica de seguranca

A execucao segue somente leitura:

- nao marcar lido;
- nao mover;
- nao excluir;
- nao criar evento;
- nao enviar WhatsApp;
- nao executar automacoes.

O projeto continua preparado para evoluir essas etapas com controles explicitos por conta.
