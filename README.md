# Assistente Pessoal

Assistente pessoal executado como Cloud Run Job para ler caixas Gmail configuradas, normalizar emails, classificar mensagens por regras, persistir historico e gerar relatorio final.

## Arquitetura principal

```text
Connector
  -> EmailEntity
  -> Classifier
  -> Persistence
  -> Automation
  -> Report
```

Essa separacao prepara a base para novos conectores, como Google Calendar, Outlook, WhatsApp e IA, sem acoplar o dominio ao formato da API do Gmail.

## Camadas

- `app/connectors`: integra com provedores externos. O `GmailConnector` retorna `EmailEntity` normalizado.
- `app/core/models.py`: define `EmailEntity`, `Classification`, `ActionPlan` e `PipelineResult`.
- `app/core/classifier.py`: classificador por regras com categoria, prioridade, razao e confianca.
- `app/storage/persistence.py`: camada de persistencia Firestore com upsert/deduplicacao.
- `app/core/automation.py`: planeja acoes em `dry_run`, sem executar mutacoes.
- `app/core/report.py`: consolida totais por conta, categoria, prioridade, erros, acoes planejadas e duracao.
- `app/core/daily_job.py`: orquestra o pipeline.

## EmailEntity

Campos internos normalizados:

- `id`
- `provider`
- `account_id`
- `account_email`
- `thread_id`
- `subject`
- `sender`
- `recipients`
- `snippet`
- `labels`
- `received_at`
- `raw_headers`
- `metadata`

Detalhes especificos do Gmail ficam em `metadata`; o restante do sistema trabalha apenas com a entidade interna.

## Classificacao

Categorias:

```text
financeiro, compra, entrega, evento, trabalho, seguranca, promocao,
newsletter, social, educacao, viagem, saude, outros
```

Prioridades:

```text
critica, alta, normal, baixa, ruido
```

O classificador corrige falsos positivos comuns:

- promocao com data, desconto ou `24h` nao vira evento;
- tutorial/newsletter nao vira evento;
- oferta de emprego vira `trabalho` com prioridade `normal`, exceto quando houver entrevista, prazo, convite ou resposta direta.

## Persistencia

Colecoes usadas:

```text
runs/
accounts/<account_id>/emails/<message_id>
```

Cada email e salvo com:

- entidade normalizada;
- classificacao;
- acoes planejadas;
- `first_seen_at` na primeira vez;
- `last_seen_at` em todo processamento.

O uso de merge/upsert evita duplicacao. Se o email ja existe, ele e atualizado com novo `last_seen_at` e pode ser reclassificado quando a informacao relevante mudar.

## Automacao

O Automation Planner separa decisao de classificacao e plano de acao. Cada plano contem:

- `type`
- `reason`
- `dry_run`
- `status`

Nesta fase nada e executado; as acoes entram apenas no relatorio e na persistencia.

## Seguranca operacional

`DRY_RUN=true` deve permanecer ativo. O job:

- nao marca email como lido;
- nao move;
- nao exclui;
- nao cria evento;
- nao envia WhatsApp;
- nao executa nenhuma automacao externa.

## Configuracao de contas

As contas ficam em `config/accounts.yaml`. Para adicionar uma conta Gmail, inclua uma entrada:

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

## Deploy

A infraestrutura existente permanece inalterada. Use os comandos atuais:

```bash
make deploy
make run-job
make list-jobs
```
