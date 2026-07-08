# ADR-006 — Context Engine

Status: proposto

## Contexto

Classificação isolada não basta. O sistema precisa entender continuidade: mensagens sobre a mesma compra, reagendamento de reunião, vencimento de cobrança, cancelamento, confirmação e atualização.

## Decisão

Criar futuramente um `ContextEngine` entre classificação e planejamento.

Fluxo alvo:

```text
WorkItem
↓
Classifier
↓
ContextEngine
↓
AutomationPlanner
```

O ContextEngine responde:

- este item é novo?
- atualiza algo existente?
- cancela algo?
- pertence ao mesmo assunto?
- já foi resolvido?
- deve gerar nova ação ou atualizar ação anterior?

## Consequências

- Reduz duplicidade de ações.
- Permite acompanhar assuntos ao longo do tempo.
- Melhora relatórios e resumos.

## Alternativas descartadas

- Tratar cada e-mail como evento isolado para sempre.
- Deixar a IA resolver contexto sem persistência estruturada.
