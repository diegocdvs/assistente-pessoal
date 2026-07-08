# ADR-004 — Separação entre AutomationPlanner e AutomationExecutor

Status: aceito

## Contexto

O sistema precisa sugerir ações, mas ações externas podem ser destrutivas ou sensíveis: marcar e-mail como lido, arquivar, criar evento, enviar WhatsApp.

## Decisão

Separar planejamento e execução:

```text
AutomationPlanner -> cria ActionPlan
AutomationExecutor -> executa ActionPlan quando permitido
```

Enquanto `DRY_RUN=true`, o executor não deve executar ações reais.

## Consequências

- Ações são auditáveis.
- Segurança fica explícita.
- É possível exigir aprovação humana antes da execução.

## Alternativas descartadas

- Classificador executar ações.
- Conector executar ações durante leitura.
- IA executar diretamente APIs externas.
