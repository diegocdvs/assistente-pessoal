# ADR-002 — WorkItem como contrato interno

Status: aceito

## Contexto

O sistema processará e-mails, eventos, mensagens, documentos e tarefas. Cada fonte tem modelo próprio, mas o núcleo precisa tratar todos como itens processáveis.

## Decisão

Criar e manter `WorkItem` como contrato genérico para itens que entram no pipeline.

Campos conceituais:

```text
id
source
type
account_id
payload
created_at
metadata
```

## Consequências

- IA pode operar sobre `WorkItem`, não sobre Gmail/Outlook/Calendar.
- Automação pode receber itens normalizados.
- Novos conectores convergem para o mesmo domínio.

## Alternativas descartadas

- Um modelo diferente por pipeline.
- Passar payload bruto de APIs externas para o núcleo.
