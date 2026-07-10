# Engineering Constitution

## Principios

1. Conectores leem e normalizam dados; nao executam regras de seguranca proprias.
2. Conteudo externo deve passar pela Security Capability antes de qualquer automacao futura.
3. IA futura consome contexto e assessments, nunca provedores diretamente.
4. `DRY_RUN=true` e a postura padrao para qualquer acao externa.
5. Nenhum link deve ser acessado durante analise estatica.
6. Nenhum anexo deve ser baixado, aberto ou executado durante analise estatica.
7. Decisoes de seguranca precisam ser auditaveis.

## Camadas

```text
Provider data
  -> Domain Entity
  -> Security Capability
  -> ContextSnapshot
  -> Future consumers
```

Qualquer modulo novo deve reutilizar `app/security`.
