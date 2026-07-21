# Padrões de desenvolvimento, agentes e versionamento no GitHub

Este documento define a regra operacional para trabalhos técnicos conduzidos com Diego.

## Regra principal

Tudo que envolver desenvolvimento técnico, agentes de IA, automações, integrações, webhooks, bots, pipelines, monitoramentos, arquitetura de software, scripts reutilizáveis ou documentação técnica executável deve ser criado, documentado e salvo no GitHub.

O Google Drive pode continuar sendo usado para documentação de leitura, especificações, planejamento e material de estudo, mas o GitHub deve ser a fonte versionada para código, prompts técnicos, arquitetura implementável, agentes e pacotes reutilizáveis.

## Ordem de trabalho técnico

1. Codex
2. Lovable
3. Outros recursos/ferramentas

## Regra de repositório

Quando o projeto já tiver repositório próprio, todo novo desenvolvimento deve ser salvo nele.

Quando o projeto ainda não tiver repositório próprio, o desenvolvimento deve ser salvo provisoriamente em um repositório central adequado, preferencialmente `diegocdvs/assistente-pessoal`, em uma pasta clara por projeto.

## Convenção de pastas

Usar nomes explícitos e estáveis, por exemplo:

```txt
projects/<nome-do-projeto>/
agents/<nome-do-agente>/
packages/<nome-do-pacote>/
docs/<tema-ou-padrao>/
```

## Segurança

Nunca salvar no GitHub:

- tokens reais;
- chaves de API;
- senhas;
- dados pessoais sensíveis;
- credenciais de banco;
- secrets de Telegram, Google Cloud, GitHub, provedores de e-commerce ou equivalentes.

Usar sempre `.env.example`, Secret Manager, GitHub Secrets ou variáveis protegidas do ambiente.

## Monitoramento transversal

Projetos com webhook, endpoint público, API, bot, automação externa, job agendado, alerta, Cloud Run, GitHub Actions, Google Apps Script, Discord, Telegram ou integração equivalente devem ser avaliados para integração com o pacote `webhook-monitor-telegram`.

Chave padrão:

```txt
project_id + provider + webhook_name + event_key
```

## Status

Regra aceita como padrão operacional a partir de 21/07/2026.
