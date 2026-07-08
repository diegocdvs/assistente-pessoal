# North Star — Assistente Pessoal

## Problema central

O projeto existe para reduzir a carga operacional e cognitiva do usuário ao transformar fluxos dispersos de informação — e-mail, agenda, mensagens, documentos e tarefas — em decisões, prioridades, lembretes e ações rastreáveis.

## Promessa do produto

Todos os dias, o Assistente Pessoal deve responder:

1. O que exige minha atenção agora?
2. O que posso ignorar?
3. O que precisa virar compromisso, tarefa, alerta ou acompanhamento?
4. O que mudou desde a última execução?
5. O que eu preciso saber antes de começar ou encerrar o dia?

## Critério de valor

Uma funcionalidade só entra no roadmap se reduzir pelo menos um destes pontos:

- tempo gasto revisando caixas de entrada;
- risco de esquecer prazos, compromissos ou cobranças;
- dispersão entre canais;
- retrabalho operacional;
- dependência de verificação manual;
- ruído informacional.

## Meta da versão 1.0

Até a versão 1.0, o sistema deve operar diariamente e entregar:

- leitura de Gmail e Outlook;
- leitura de agenda Google;
- classificação e priorização;
- persistência no Firestore;
- planos de ação auditáveis;
- resumo diário por WhatsApp;
- diagnóstico operacional por comandos `make`;
- arquitetura extensível para novos conectores.

## Não objetivos

O projeto não deve virar:

- um chatbot genérico;
- um script isolado;
- um sistema que executa ações externas sem auditoria;
- um produto dependente de um único provedor de IA;
- um conjunto de integrações acopladas ao `DailyJob`.

## Princípio decisório

Quando houver conflito entre velocidade e arquitetura, escolher o menor incremento que entregue valor real sem quebrar a direção arquitetural.

Quando houver conflito entre automação e segurança, escolher segurança e `DRY_RUN`.
