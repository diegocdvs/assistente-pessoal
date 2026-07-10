# Security Policy

Status: normativa

## Principios

Todo dado externo e nao confiavel por padrao. O sistema deve aplicar defesa em profundidade, menor privilegio, isolamento, rastreabilidade e falha segura.

## Regras para e-mail e conteudo externo

- Nao executar HTML, JavaScript, macros ou binarios.
- Nao abrir anexos automaticamente.
- Nao acessar links automaticamente.
- Nao seguir redirects automaticamente.
- Nao baixar conteudo remoto de mensagens.
- Nao realizar scraping para unsubscribe.
- Validar headers, MIME, extensoes, URLs e dominios antes de qualquer acao.
- Acoes externas permanecem em `DRY_RUN` ate aprovacao explicita.

## Threat Analyzer alvo

A camada de seguranca devera produzir:

- `risk_score`;
- `risk_level`;
- `risk_reasons`;
- politica para links;
- politica para anexos;
- evidencias de autenticacao disponiveis, como SPF, DKIM e DMARC;
- sinais de phishing e spoofing;
- recomendacao de quarentena ou revisao.

## Secrets e identidade

- Segredos ficam no Secret Manager.
- Service Accounts seguem menor privilegio.
- OAuth usa apenas os escopos necessarios.
- Tokens nao aparecem em logs.
- Rotacao e revogacao devem ser documentadas.

## Logs e privacidade

- Nao registrar corpo completo, tokens, senhas ou dados sensiveis desnecessarios.
- Logs devem usar identificadores tecnicos e `run_id`.
- Dados enviados futuramente a LLMs exigem policy propria e minimizacao.

## Supply chain

- Dependencias devem ser mantidas, versionadas e verificadas contra vulnerabilidades.
- Bibliotecas abandonadas ou desnecessarias nao devem entrar.
- Novos providers exigem threat model e revisao de permissoes.

## Incidentes

Quando houver suspeita de comprometimento:

1. interromper automacoes mutaveis;
2. revogar tokens afetados;
3. rotacionar secrets;
4. preservar logs de auditoria;
5. avaliar alcance e dados expostos;
6. registrar causa e acao corretiva.
