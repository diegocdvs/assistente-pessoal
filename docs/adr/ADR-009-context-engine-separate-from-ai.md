# ADR-009 - Context Engine separado da IA

Status: aceito  
Data: 2026-07-09

## Contexto

O sistema ja coleta, normaliza, classifica, persiste e planeja acoes. Antes de adicionar IA, e necessario consolidar uma visao operacional deterministica do usuario.

## Decisao

Criar `ContextEngine` como camada propria. Ele gera `ContextSnapshot` usando apenas dados persistidos e modelos de dominio.

A IA futura deve consumir `ContextSnapshot`. Ela nao deve consultar Firestore, Gmail, Outlook, Calendar, WhatsApp ou APIs externas diretamente.

## Motivos

- Separar dados, contexto, IA e execucao.
- Tornar contexto testavel sem LLM.
- Evitar que prompts carreguem logica de negocio ou consultas de infraestrutura.
- Permitir Dashboard, WhatsApp e Planner usando o mesmo contrato.

## Alternativas descartadas

- Deixar a IA buscar dados diretamente.
- Criar resumo operacional dentro do `DailyJob`.
- Fazer cada consumer consultar Firestore diretamente.
- Usar embeddings/vetores antes de ter contexto deterministico.

## Consequencias

- O Context Engine vira a API unica para consumidores de contexto.
- O dominio continua independente de provedores externos.
- IA futura tera entrada consistente, auditavel e testavel.
- Novas heuristicas de contexto podem evoluir sem tocar em conectores.
