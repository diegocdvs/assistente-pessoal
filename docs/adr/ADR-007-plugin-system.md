# ADR-007 — Plugin System

Status: proposto

## Contexto

O projeto deve adicionar novos conectores e notificadores sem alterar continuamente o núcleo.

## Decisão

Evoluir para um sistema de plugins.

Estrutura alvo:

```text
plugins/
  gmail/
  outlook/
  calendar/
  whatsapp/
  drive/
```

Cada plugin pode conter:

```text
connector.py
notifier.py
config.py
tests.py
```

## Consequências

- Novas integrações ficam isoladas.
- O core permanece estável.
- Fica possível criar SDK interno no futuro.

## Alternativas descartadas

- Crescer `app/connectors` indefinidamente sem contrato claro.
- Registrar conectores com ifs espalhados.
