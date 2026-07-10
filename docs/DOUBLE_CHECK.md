# Double Check / Audit Mode

Status: planejado

## Objetivo

Verificar periodicamente, de forma independente e somente leitura, se o agente esta lendo, normalizando, classificando e persistindo os dados corretamente.

## Configuracao prevista

```env
DOUBLE_CHECK_ENABLED=true
DOUBLE_CHECK_INTERVAL_HOURS=48
DOUBLE_CHECK_LOOKBACK_HOURS=72
DOUBLE_CHECK_SAMPLE_SIZE=50
DOUBLE_CHECK_SELF_HEAL=false
```

O scheduler pode chamar diariamente, mas a auditoria so executa quando a ultima auditoria bem-sucedida tiver pelo menos 48 horas.

## Fluxo

```text
Provider
 -> releitura controlada
 -> normalizacao independente
 -> comparacao com Persistence
 -> AuditReport
 -> alerta somente se houver divergencia
```

## Verificacoes

- itens presentes na origem e ausentes no Firestore;
- documentos duplicados;
- EmailEntity sem WorkItem;
- WorkItem sem Classification;
- Classification sem persistencia;
- ActionPlan ausente quando exigido por regra;
- conta/provider incorreto;
- campos obrigatorios incompletos;
- divergencia de schema_version;
- execucoes interrompidas ou silenciosamente parciais;
- gaps de leitura por janela temporal.

## Modelos previstos

### AuditRun

- audit_run_id;
- started_at;
- finished_at;
- lookback;
- accounts_checked;
- source_items_checked;
- records_checked;
- discrepancies_count;
- status;
- schema_version.

### AuditDiscrepancy

- type;
- severity;
- provider;
- account_id;
- source_id;
- expected_state;
- actual_state;
- detected_at;
- suggested_action;
- evidence;
- status.

## Persistencia prevista

```text
audit_runs/{audit_run_id}
audit_runs/{audit_run_id}/discrepancies/{discrepancy_id}
```

## Estados

- OK: nenhuma divergencia material.
- WARNING: divergencias recuperaveis ou amostra incompleta.
- ERROR: perda de dados, falha sistematica ou impossibilidade de auditar.

## Seguranca

- somente leitura por padrao;
- sem abrir anexos;
- sem acessar links;
- sem executar ActionPlans;
- sem apagar ou sobrescrever registros;
- `DOUBLE_CHECK_SELF_HEAL=false` ate existir policy, auditoria e aprovacao explicita.

## Etapas

### Fase 1

- contratos `AuditRun` e `AuditDiscrepancy`;
- repository in-memory;
- reconciliacao deterministica;
- testes unitarios.

### Fase 2

- Firestore repository;
- releitura por provider;
- feature flag;
- relatorio operacional.

### Fase 3

- agendamento a cada 48 horas;
- alertas;
- metricas de completude e divergencia.

### Fase 4 futura

- self-heal limitado, idempotente e desligado por padrao;
- nenhuma correcao automatica sem trilha de auditoria.

## Criterio de aceite

O modo deve demonstrar, com evidencia, a correspondencia entre origem, entidades normalizadas, classificacoes, ActionPlans e persistencia, sem modificar qualquer dado auditado.
