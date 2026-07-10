# Engineering Constitution

Status: normativa

## Principio central

Nenhuma funcionalidade nova entra enquanto a fundacao de engenharia necessaria para sustenta-la nao estiver definida.

O projeto evolui na ordem:

```text
Foundation -> Capability -> Release -> Feature
```

## Pilares obrigatorios

- Security by Design.
- Privacy by Design.
- Observability by Design.
- Documentation by Design.
- Testability by Design.
- Reproducibility by Design.
- Least Privilege.
- Zero Trust para dados externos.
- Backward Compatibility.
- Dry Run antes de mutacoes reais.

## Gates antes de implementar

Toda funcionalidade deve ter, quando aplicavel:

1. arquitetura e contratos;
2. threat model;
3. classificacao de dados;
4. estrategia de testes;
5. observabilidade;
6. runbook e rollback;
7. criterios de aceite;
8. ADR para decisoes relevantes.

## Regras imutaveis

- O dominio nao depende de providers externos.
- Connectors nao executam regras de negocio.
- Conteudo externo nunca e executado automaticamente.
- Links nunca sao acessados automaticamente.
- Anexos nunca sao abertos automaticamente.
- Nenhuma credencial e versionada.
- Nenhuma decisao importante fica apenas em conversa.
- Nenhuma release nova inicia antes da anterior estar mergeada e validada em `main`.
- Toda acao mutavel exige autorizacao explicita ou policy previamente aprovada.

## Definition of Done

Uma entrega so esta concluida quando:

- testes passam;
- compileall passa;
- documentacao esta sincronizada;
- riscos estao registrados;
- smoke/release passam quando aplicavel;
- nenhum segredo foi exposto;
- PR foi revisado;
- `main` foi validada apos merge.
