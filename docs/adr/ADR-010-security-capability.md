# ADR-010 - Security Capability

Status: aceito  
Data: 2026-07-10

## Contexto

Gmail, Outlook, IMAP, Calendar, WhatsApp, Dashboard, Subscription Manager e IA futura processarao conteudo externo. Se cada modulo implementar seguranca propria, o projeto ficara inconsistente e dificil de auditar.

## Decisao

Criar `app/security` como Security Capability reutilizavel.

Toda validacao de conteudo externo deve passar por essa camada. Connectors e providers nao devem implementar regras proprias de phishing, spoofing, anexo, link, dominio ou policy.

## Consequencias

- Seguranca vira contrato de plataforma.
- `ThreatAnalyzer` produz `SecurityAssessment` auditavel.
- `RiskEngine` e `SecurityPolicy` ficam centralizados.
- Futuros modulos podem consumir eventos sem reimplementar analise.
- Nenhuma acao automatica e executada nesta release.

## Alternativas descartadas

- Colocar validacao dentro de cada connector.
- Deixar IA decidir seguranca diretamente.
- Acessar links para reputacao nesta fase.
- Abrir anexos ou usar sandbox nesta fase.

## Regras

- Nunca acessar links durante analise estatica.
- Nunca abrir anexos durante analise estatica.
- Nunca executar unsubscribe automaticamente.
- Nunca executar quarentena real sem release propria.
