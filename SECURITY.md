# Security

## Security Capability

Release 0.5 cria `app/security` como camada unica de analise estatica.

Ela fornece:

- `ThreatAnalyzer`;
- `SecurityAssessment`;
- analisadores de headers, links, anexos e dominios;
- `RiskEngine`;
- `SecurityPolicy`;
- eventos internos;
- audit trail.

## Garantias

- Nao acessa links.
- Nao abre anexos.
- Nao executa unsubscribe.
- Nao move, exclui, marca ou envia mensagens.
- Nao chama IA, ML, sandbox ou APIs externas.
- Subscription Management nao acessa URLs, nao envia `mailto`, nao faz scraping e nao abre navegador.
- Planos de unsubscribe exigem aprovacao e permanecem `execution_enabled=false`.

## Decisoes

Decisoes possiveis:

```text
allow
warn
review
block
quarantine
```

Na Release 0.5, essas decisoes sao apenas retornadas. A Release 0.7 usa risco alto/critico para impedir planos executaveis de unsubscribe e exigir revisao manual. Nenhum bloqueio real e executado.

## Uso

```python
from app.security import ThreatAnalyzer

assessment = ThreatAnalyzer().analyze(email.to_dict())
```

Toda integracao futura deve usar essa capability em vez de criar seguranca propria.
