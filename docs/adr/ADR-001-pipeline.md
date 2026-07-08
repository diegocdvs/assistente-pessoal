# ADR-001 — Pipeline principal

Status: aceito

## Contexto

O projeto precisa processar informações de múltiplas fontes sem acoplar regras de negócio a provedores específicos.

## Decisão

O pipeline principal será:

```text
Connector
↓
Domain Entity
↓
WorkItem
↓
Classifier
↓
Persistence
↓
AutomationPlanner
↓
Report
```

## Consequências

- O `DailyJob` atua como orquestrador, não como dono da lógica.
- Conectores não classificam nem persistem.
- Classificação não executa ações.
- Persistência fica centralizada.

## Alternativas descartadas

- Pipeline específico para Gmail.
- IA chamando APIs externas diretamente.
- Conectores gravando no Firestore.
