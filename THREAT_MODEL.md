# Threat Model

## Escopo

O Assistente Pessoal processa conteudo externo de e-mail e futuros providers. A Release 0.5 cobre apenas analise estatica.

## Ativos

- caixa de entrada do usuario;
- credenciais OAuth e Secret Manager;
- Firestore;
- contexto operacional;
- futuros canais de acao como Calendar, WhatsApp e Dashboard.

## Ameacas iniciais

- phishing por links encurtados ou dominios parecidos;
- spoofing por headers divergentes;
- anexos executaveis;
- tracking por imagens externas;
- unsubscribe malicioso;
- conteudo que tenta induzir automacoes futuras.

## Controles

- `ThreatAnalyzer` centralizado;
- `RiskEngine` deterministico;
- `SecurityPolicy`;
- eventos internos;
- `SecurityAuditRecord`;
- `DRY_RUN=true`;
- nenhuma execucao de links/anexos/unsubscribe.

## Fora de escopo nesta release

- VirusTotal;
- Google Safe Browsing;
- Microsoft Defender;
- ClamAV;
- sandbox;
- IA/ML;
- quarentena real.
