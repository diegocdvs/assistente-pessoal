# Threat Model

Status: inicial e obrigatorio para novas capacidades

## Ativos protegidos

- credenciais OAuth e tokens;
- e-mails e metadados;
- classificacoes e ActionPlans;
- dados pessoais e financeiros;
- historico operacional;
- configuracoes e feature flags;
- identidade do usuario.

## Fronteiras de confianca

```text
Google / Microsoft / futuros providers
        -> Connectors
        -> Security Layer
        -> Domain
        -> Persistence
        -> Consumers futuros (WhatsApp, Dashboard, LLM)
```

Todo cruzamento deve validar entrada, limitar privilegios e registrar auditoria.

## Ameacas prioritarias

1. Phishing e links maliciosos.
2. Anexos com malware, macros ou extensoes enganosas.
3. Spoofing de remetente e dominios homografos.
4. Vazamento de tokens e secrets.
5. Prompt injection futura via conteudo externo.
6. Duplicidade, perda ou classificacao incorreta de dados.
7. Acoes mutaveis sem autorizacao.
8. Unsubscribe malicioso via URL, redirect, `mailto` ou header forjado.
9. Dependencias comprometidas.
10. Logs contendo dados sensiveis.
11. Falha silenciosa na leitura ou persistencia.

## Mitigacoes atuais

- leitura via APIs;
- sem execucao de anexos, HTML ou JavaScript;
- `DRY_RUN=true`;
- Secret Manager;
- conectores read-only;
- logs estruturados;
- testes, doctor, smoke e release;
- Double Check planejado para reconciliacao.

## Mitigacoes obrigatorias futuras

- Threat Analyzer antes do uso do conteudo;
- validacao de URLs e MIME;
- quarantine/review para alto risco;
- politica de dados para LLMs;
- auditoria de dependencias;
- confirmacao explicita para unsubscribe e demais mutacoes;
- Double Check independente e read-only.
- Subscription Management separado de qualquer executor, com aprovacao explicita e targets redigidos.

## Regra de atualizacao

Toda nova integracao, capability ou acao mutavel deve atualizar este documento e registrar riscos residuais antes da implementacao.
