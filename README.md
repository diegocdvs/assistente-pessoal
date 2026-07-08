# Assistente Pessoal

Assistente pessoal executado como Cloud Run Job para ler contas configuradas, normalizar mensagens, classificar, persistir, planejar acoes seguras e gerar relatorio final.

## Sprint 1.5

A base foi consolidada em um pipeline desacoplado:

```text
Connector
  -> EmailEntity
  -> Classifier
  -> Persistence
  -> Automation
  -> Report
```

O `DailyJob` orquestra o fluxo e depende de abstracoes:

- `ConnectorManager`
- `Classifier`
- `Persistence`
- `AutomationPlanner`
- `Reporter`

Ele nao instancia `GmailConnector` diretamente.

## Camadas

- `app/connectors/gmail.py`: conector Gmail que retorna `EmailEntity` e nao executa mutacoes.
- `app/connectors/manager.py`: registra conectores por provider. Hoje registra `gmail`; a estrutura esta pronta para `outlook`, `calendar` e `whatsapp`.
- `app/core/models.py`: `EmailEntity`, `WorkItem`, `Classification`, `ActionPlan` e `PipelineResult`.
- `app/core/classifier.py`: classificador por regras com categoria, prioridade, confianca, motivo e `possible_event`.
- `app/storage/persistence.py`: persistencia Firestore com upsert/deduplicacao.
- `app/core/automation.py`: gera `ActionPlan` em `dry_run`, sem executar acoes reais.
- `app/core/report.py`: consolida totais e tempo de execucao.

## Modelos

`EmailEntity`:

```text
id, provider, account_id, account_email, thread_id, subject, sender,
recipients, snippet, labels, received_at, raw_headers, metadata
```

`WorkItem`:

```text
id, source, type, account_id, payload, created_at
```

`ActionPlan`:

```text
type, reason, dry_run, status, payload
```

## Classificacao

Categorias:

```text
financeiro, compra, entrega, evento, trabalho, seguranca, promocao,
newsletter, social, educacao, viagem, saude, sistema, outros
```

Prioridades:

```text
critica, alta, normal, baixa, ruido
```

Regras importantes:

- promocao com `24h`, `oferta`, `desconto` ou percentual nao vira evento;
- tutorial nao vira evento;
- newsletter nao vira evento;
- ofertas de emprego viram `trabalho` com prioridade `normal`, salvo entrevista, convite, prazo ou resposta direta;
- recibo/compra vai para `compra` ou `financeiro`, nao para evento.

## Firestore

Estrutura:

```text
runs/{run_id}
accounts/{account_id}/emails/{message_id}
accounts/{account_id}/classifications/{message_id}
accounts/{account_id}/action_plans/{message_id}
```

A persistencia usa merge/upsert. Emails existentes atualizam `last_seen_at`; emails novos recebem `first_seen_at`. Isso evita duplicacao por `message_id`.

## Seguranca

`DRY_RUN=true` permanece como regra operacional. O job nao:

- marca lido;
- move mensagens;
- exclui mensagens;
- cria eventos;
- envia WhatsApp;
- executa automacoes externas.

O GmailConnector usa os escopos `gmail.modify` e `calendar.events` porque o refresh token de producao foi emitido com eles. Mesmo assim, o codigo atual apenas le mensagens e nao chama endpoints mutaveis.

## Configuracao de contas

As contas ficam em `config/accounts.yaml`. Para adicionar uma conta Gmail:

```yaml
accounts:
  - id: pessoal_google
    label: Pessoal
    provider: gmail
    email: pessoa@example.com
    enabled: true
    secret_prefix: google-pessoal
    max_emails: 10
    firestore:
      enabled: true
```

Secrets esperados:

```text
<secret_prefix>-client-secret-json
<secret_prefix>-refresh-token
```

## Testes

```bash
python -m pytest
```

Validacao completa:

```bash
make validate
```

O comando executa:

```bash
python -m pytest
python -m compileall app scripts
```

## Diagnostico

Use `make doctor` para validar ambiente, projeto GCP, APIs, secrets e Cloud Run Job:

```bash
make doctor
```

A saida usa:

```text
[OK]
[WARN]
[ERROR]
```

O comando falha se encontrar erros de configuracao obrigatoria.

## Validacao operacional

Depois do merge:

```bash
make validate
make doctor
make deploy
make smoke
```

Fluxo completo:

```bash
make release
```

Smoke test:

```bash
make smoke
```

O smoke executa o job, identifica a execucao, le logs para detectar erros conhecidos e validar sinais basicos. Se o report JSON estiver truncado nos logs, ele faz fallback para Firestore e exige documentos em `emails` e `classifications`; `action_plans` vazio gera `WARN`, nao falha.

Verifique no Firestore:

- novo documento em `runs`;
- documentos em `accounts/<account_id>/emails`;
- documentos em `accounts/<account_id>/classifications`;
- documentos em `accounts/<account_id>/action_plans`;
- nenhuma alteracao na caixa Gmail.

## Infraestrutura

Dockerfile, Makefile, Cloud Build, Cloud Run e infraestrutura GCP permanecem inalterados.
