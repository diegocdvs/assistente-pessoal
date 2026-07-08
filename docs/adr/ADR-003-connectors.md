# ADR-003 — Conectores isolados

Status: aceito

## Contexto

Gmail, Outlook, Calendar, WhatsApp e Drive possuem APIs, autenticação e payloads diferentes. O núcleo não deve conhecer essas diferenças.

## Decisão

Cada provedor deve ter um conector isolado registrado em um `ConnectorManager`.

O conector deve:

- autenticar;
- ler dados externos;
- normalizar para entidade interna;
- devolver itens ao pipeline.

O conector não deve:

- classificar;
- persistir;
- executar ação;
- gerar relatório.

## Consequências

- Novos provedores entram sem alterar o pipeline principal.
- Testes ficam isolados por provedor.
- Troca de API externa tem baixo impacto.

## Alternativas descartadas

- `DailyJob` instanciar cada conector diretamente.
- Um conector genérico com ifs por provedor.
