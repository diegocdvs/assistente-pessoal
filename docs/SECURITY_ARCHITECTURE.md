# Security Architecture - Release 0.5

Status: fundacao estrutural  
Escopo: analise estatica e reutilizavel para todos os providers futuros.

## Objetivo

Criar uma Security Capability unica em `app/security`.

Nenhum connector, provider, Context Engine, IA futura ou modulo de automacao deve implementar seguranca propria.

## Fluxo

```text
EmailEntity / payload persistido
        |
        v
ThreatAnalyzer
        |
        +--> HeaderAnalyzer
        +--> LinkAnalyzer
        +--> AttachmentAnalyzer
        +--> DomainAnalyzer
        |
        v
RiskEngine
        |
        v
SecurityPolicy
        |
        v
SecurityAssessment + SecurityEvent + SecurityAuditRecord
```

## ThreatAnalyzer

`ThreatAnalyzer` produz `SecurityAssessment`.

Ele:

- nao modifica dados;
- nao acessa links;
- nao abre anexos;
- nao chama APIs externas;
- nao executa decisoes.

## SecurityAssessment

Campos principais:

```text
assessment_id
provider
source_id
risk_score
risk_level
risk_reasons
link_count
attachment_count
external_images
suspicious_headers
spoofing_signals
authentication_signals
created_at
schema_version
policy_decision
```

## Header Analyzer

Detecta:

- `List-Unsubscribe`;
- `List-ID`;
- `Auto-Submitted`;
- `Precedence`;
- `Reply-To` diferente;
- `Return-Path`;
- SPF, DKIM e DMARC em `Authentication-Results`;
- headers suspeitos.

## Link Analyzer

Analise estatica. Nunca acessa URLs.

Detecta:

- protocolo;
- dominio;
- parametro de redirect;
- IP literal;
- URL encurtada;
- unicode;
- punycode;
- porta incomum;
- quantidade.

## Attachment Analyzer

Analise estatica. Nunca abre anexos.

Detecta:

- nome;
- extensao;
- MIME;
- tamanho;
- dupla extensao;
- tipos executaveis.

## Domain Analyzer

Detecta:

- dominio vazio;
- IP literal;
- unicode;
- punycode;
- TLD incomum;
- lookalike simples de dominios protegidos.

## Risk Engine

Algoritmo deterministico.

Exemplos de pontuacao:

- link suspeito aumenta score;
- anexo executavel aumenta score;
- dupla extensao aumenta score;
- SPF/DKIM/DMARC invalido aumenta score;
- imagens externas aumentam score limitado.

Niveis:

```text
low
medium
high
critical
```

## Policy

Decisoes:

```text
allow
warn
review
block
quarantine
```

Na Release 0.5, nenhuma decisao e executada automaticamente.

## Eventos

Eventos internos:

```text
HighRiskDetected
SuspiciousAttachment
SpoofingDetected
SubscriptionDetected
LinkWarning
```

Esses eventos serao consumidos futuramente por Double Check, Dashboard, IA e automacoes com aprovacao.

## Context Engine

`ContextSnapshot` passa a expor:

```text
high_risk_items
warning_items
security_events
```

Esses campos sao derivados de `ThreatAnalyzer` sem executar acoes.

## Double Check

Toda `SecurityAssessment` e serializavel e pode ser revalidada futuramente. A Release 0.5 nao implementa scheduler nem revalidacao automatica.

## Subscription Manager

`List-Unsubscribe` e analisado como sinal de seguranca antes de qualquer unsubscribe futuro.

Na Release 0.7, o Communication Manager consome `SecurityAssessment` para preencher risco em `SubscriptionEntity` e bloquear qualquer plano executavel quando houver risco `high`, `critical`, `block` ou `quarantine`.

O sistema continua proibido de:

- acessar links de unsubscribe;
- seguir redirects;
- enviar `mailto`;
- fazer scraping;
- abrir navegador;
- executar unsubscribe.

## Calendar

`CalendarSecurityAnalyzer` avalia metadados de `CalendarEvent` de forma estatica:

- links presentes em titulo, local ou resumo de descricao;
- meeting URL presente;
- organizador externo;
- dominio suspeito;
- sinais de convite inesperado.

Ele nao acessa URLs, nao entra em reunioes, nao abre anexos, nao aceita e nao rejeita convites.

## Daily Brief

Daily Brief resume alertas de seguranca ja presentes no `ContextSnapshot`. Ele nao recalcula reputacao externa, nao acessa links e nao transforma alertas em acoes automaticas.

## Scheduled Daily Brief

O agendamento diario adiciona risco de duplicidade e envio indevido. A mitigacao fica em `app/scheduled_daily_brief`:

- acquire idempotente antes de gerar/entregar;
- destinatario redigido por hash;
- nenhuma persistencia de corpo/HTML;
- `delivery_uncertain` sem retry automatico;
- Cloud Scheduler autenticado sem endpoint publico;
- modo inicial `draft`.
