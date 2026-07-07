# Proximos passos

## Validacao operacional

1. Confirmar que cada conta habilitada em `config/accounts.yaml` possui secrets:

```text
<secret_prefix>-client-secret-json
<secret_prefix>-refresh-token
```

2. Executar o Cloud Run Job e verificar:

- documentos novos em `runs`;
- documentos em `processed_emails`;
- ausencia de alteracoes na caixa Gmail.

## Sprint 2 sugerida

- Implementar conector Outlook.
- Adicionar deteccao estruturada de eventos sem criar eventos automaticamente.
- Criar relatorio consolidado por conta.
- Adicionar metricas de execucao e alarmes.
- Preparar camada de IA como fallback quando regras nao classificarem bem.
- Evoluir politicas por conta sem permitir mutacoes por padrao.

## Operacao

Comandos existentes:

```bash
make deploy
make run-job
make list-jobs
```

O Makefile e a infraestrutura GCP permanecem como fonte operacional atual.
