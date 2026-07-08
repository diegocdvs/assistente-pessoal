# Architecture Review - Release 0.1

Status: revisao arquitetural pos Release 0.1  
Escopo: auditoria tecnica para evolucao ate a versao 1.0  
Premissas: Gmail, Firestore, Cloud Run Job e pipeline operacional validados  
Restricao: nenhuma mudanca de codigo proposta como implementacao imediata neste documento

## Nota pos Release 0.2

A Release 0.2 - Foundation Hardening endereca parte das recomendacoes deste review sem adicionar novos conectores:

- `EmailEntity` agora pode ser convertido para `WorkItem`;
- o pipeline cria `WorkItem` conceitual para cada e-mail processado;
- `ActionPlan` ganhou campos auditaveis;
- `Settings` centraliza feature flags e limites basicos;
- `run_id`, `stage_counts` e `schema_version` foram adicionados ao fluxo operacional.

Permanecem como proximos riscos a tratar: multi-conta real, doctor/smoke orientados por todas as contas habilitadas, historico de reclassificacao e politica de retencao.

## 1. Sumario executivo

A Release 0.1 esta em bom estado para um produto inicial: o MVP placeholder foi removido, o fluxo principal esta funcional, o `DailyJob` deixou de depender diretamente do Gmail, os dados externos sao normalizados em `EmailEntity`, a persistencia esta centralizada e existe um conjunto operacional coerente com `validate`, `doctor`, `smoke` e `release`.

O maior acerto arquitetural foi conter a complexidade. O projeto ainda e pequeno, testavel e compreensivel. A separacao entre connector, dominio, classifier, persistence, automation planner e report e correta para a fase atual.

O ponto critico e que a arquitetura documentada ja esta mais avancada que a implementacao em alguns lugares. `WorkItem` existe, mas nao participa do pipeline real. Calendar aparece como configuracao e escopo OAuth, mas nao existe como conector. `ActionPlan` e persistido de forma agregada por mensagem, nao como unidade operacional independente. Isso nao quebra a Release 0.1, mas pode gerar retrabalho se novas integracoes forem adicionadas antes de estabilizar esses contratos.

A recomendacao principal e nao correr direto para muitos provedores. Antes de ampliar canais, a Release 0.2 deveria consolidar contratos operacionais, seguranca, observabilidade e configuracao multi-conta. Depois disso, Outlook passa a ser uma boa proxima prova de arquitetura.

## 2. Arquitetura

### O que esta excelente

- O pipeline principal esta claro e simples:

```text
Connector
EmailEntity
Classifier
Persistence
AutomationPlanner
Report
```

- `DailyJob` atua como orquestrador e recebe dependencias por abstracao, o que torna testes e evolucao mais faceis.
- `GmailConnector` normaliza payload externo para `EmailEntity`, reduzindo vazamento da API Gmail para o resto do sistema.
- `FirestorePersistence` centraliza acesso ao Firestore e evita chamadas diretas espalhadas pelo core.
- `AutomationPlanner` separa decisao de acao da execucao real. Isso e essencial para seguranca.
- `Reporter` concentra agregacoes de execucao e evita relatórios montados por strings soltas.
- O projeto esta pequeno o suficiente para manter baixo custo cognitivo.
- A cobertura de testes cobre os principais contratos da Release 0.1.
- A documentacao operacional e superior ao comum para um produto nesta fase.

### O que precisa melhorar

- A arquitetura-alvo inclui `WorkItem`, mas o pipeline real ainda processa `EmailEntity` diretamente. Isso e aceitavel em 0.1, mas precisa ser resolvido antes de IA, Calendar e WhatsApp.
- `ConnectorManager` esta conceitualmente generico, mas o protocolo atual e de e-mail: `fetch_recent(account) -> list[EmailEntity]`. Calendar, WhatsApp e Drive nao cabem naturalmente nessa assinatura.
- `AccountManager` mistura detalhes de contas de e-mail com flags futuras de calendar e politicas de leitura. Isso pode crescer mal se cada integracao adicionar campos proprios no mesmo modelo.
- `ActionPlan` nao possui `id`, `created_at`, `work_item_id` ou chave propria. Hoje ele e salvo dentro de um documento por `message_id` em `plans.<type>`, o que limita historico, auditoria, replanejamento e execucao futura.
- `DailyJob` salva o e-mail antes da classificacao e depois salva classificacao e planos separadamente. Se houver falha no meio, o estado pode ficar parcialmente persistido sem marca clara de processamento incompleto.
- A documentacao possui historico de sprints e arquitetura futura junto com arquitetura atual. Isso torna mais dificil distinguir contrato vigente de aspiracao.
- `config/accounts.yaml` contem um e-mail pessoal real e contas exemplo no arquivo versionado. Nao ha token, mas ainda e dado pessoal e cria precedente ruim.
- `scripts/google_oauth_local.py` usa escopo `gmail.readonly`, enquanto o runtime usa `gmail.modify` e `calendar.events`. Essa divergencia e uma fonte real de erro operacional.

### O que pode gerar retrabalho futuro

- Adicionar Outlook antes de formalizar o contrato de connector generico pode solidificar um modelo "email-only" e dificultar Calendar/WhatsApp depois.
- Persistir `ActionPlan` agregado por mensagem pode obrigar migracao quando houver executor real, status por acao, retry, aprovacao e auditoria.
- Manter `WorkItem` como modelo nao usado pode gerar duas arquiteturas paralelas: uma documentada e outra real.
- Usar regras do classifier sem mecanismo de versao pode dificultar reclassificacao e explicacao historica.
- Usar apenas `message_id` como chave principal e suficiente para Gmail, mas talvez nao seja suficiente para provedores diferentes sem prefixo ou politica de id global.
- `smoke.py` valida por padrao `pessoal_google`, o que contradiz parcialmente a promessa de multi-conta configuravel.

### O que removeria

- Removeria do repositório qualquer conta pessoal real em `config/accounts.yaml`, substituindo por exemplo anonimo ou mantendo somente `accounts.example.yaml`.
- Removeria, ou marcaria explicitamente como legado, `app/storage/firestore_store.py`, que hoje apenas herda `FirestorePersistence` sem adicionar comportamento.
- Removeria claims de "Calendar habilitado" em configuracoes reais enquanto nao houver `CalendarConnector`.
- Removeria de docs operacionais instrucoes antigas que ainda mencionam apenas `make deploy`, `make run-job` como fonte atual quando `make release` ja existe.

### O que simplificaria

- Separaria a documentacao em tres niveis:
  - estado atual;
  - decisoes aceitas;
  - arquitetura futura.
- Tornaria `ActionPlan` uma entidade top-level de dominio antes de criar executor real.
- Introduziria `ConnectorResult` ou `DomainItem` antes de novos conectores nao-email, em vez de forcar tudo em `EmailEntity`.
- Criaria um pequeno modulo de politicas de seguranca para concentrar `DRY_RUN`, allowed actions e bloqueios mutaveis.

## 3. Escalabilidade

### 10 contas

A arquitetura atual suporta 10 contas sem mudanca estrutural, desde que cada conta leia poucos e-mails. O processamento e sequencial, mas a carga e baixa. Gargalos provaveis:

- latencia de Secret Manager por conta;
- chamadas Gmail por mensagem;
- escritas Firestore por e-mail;
- tempo total do Cloud Run Job.

Risco baixo.

### 100 contas

100 contas ja pressionam o desenho atual. O job processa contas em loop sequencial e para cada mensagem faz uma chamada `messages.get`. Com `max_emails=10`, isso implica aproximadamente 100 chamadas de listagem mais 1.000 chamadas de detalhe por execucao, alem de escritas Firestore.

Gargalos:

- tempo de execucao do Cloud Run Job;
- quotas Gmail API;
- Secret Manager acessado repetidamente;
- Firestore write throughput;
- logs volumosos;
- dificuldade de isolar falhas por conta.

Risco medio. Ainda pode funcionar, mas precisa de limites, backoff e metricas.

### 1.000 contas

1.000 contas nao devem rodar em um unico job sequencial. Mesmo com 10 mensagens por conta, seriam cerca de 10.000 detalhes de mensagens por execucao. O tempo, as quotas e o custo operacional passam a ser relevantes.

Primeiros componentes a mudar:

- particionamento de execucao por lote de contas;
- cache ou carregamento mais eficiente de secrets;
- controle de quota por provider;
- estrategia de retries por conta;
- agregacao de report por lotes;
- metricas e alertas.

Risco alto.

### 10.000 contas

10.000 contas estao fora do envelope da arquitetura atual. O modelo de Cloud Run Job unico e sequencial nao e suficiente. Nao e necessario propor microservicos ou mensageria agora, mas sera preciso particionar execucoes e provavelmente usar jobs parametrizados por shard.

Gargalos dominantes:

- Gmail API e quotas por projeto/usuario;
- Secret Manager;
- Firestore writes e crescimento de subcolecoes;
- tempo maximo de execucao;
- custo de logs;
- report final em memoria;
- operabilidade de falhas parciais.

Risco critico se perseguido sem redesenho incremental.

### Ate onde suporta hoje

O desenho atual suporta bem uma conta e provavelmente ate dezenas de contas com baixo volume. Com disciplina operacional, talvez 50 a 100 contas. Acima disso, o primeiro limite nao sera CPU, mas IO externo: Gmail API, Secret Manager, Firestore e timeout do job.

## 4. Firestore

### Pontos positivos

- A estrutura por conta e simples:

```text
runs/{run_id}
accounts/{account_id}/emails/{message_id}
accounts/{account_id}/classifications/{message_id}
accounts/{account_id}/action_plans/{message_id}
```

- A chave por `message_id` evita duplicacao para o caso atual.
- `merge=True` reduz risco de sobrescrever campos futuros.
- `first_seen_at` e `last_seen_at` sao boas bases para idempotencia.

### Riscos

- `runs/{run_id}` nao guarda explicitamente o id no payload antes de salvar, porque o id e gerado pelo Firestore. Isso dificulta correlacao se o report impresso nao contem `run_id`.
- `save_run` cria documento com id aleatorio, nao deterministico. Isso e ok para historico, mas dificulta reconciliacao externa.
- `classifications/{message_id}` sobrescreve a classificacao atual. Nao ha historico de reclassificacoes nem versao da regra.
- `action_plans/{message_id}` agrega planos por tipo em campos aninhados. Isso limita consultas por status, tipo, data, prioridade e execucao.
- `accounts/{account_id}` nao parece ser inicializado com metadados da conta. Subcolecoes podem existir sem documento pai informativo.
- Nao ha estrategia de retencao ou arquivamento.
- Nao ha indices documentados para consultas futuras.

### Mudaria a modelagem?

Para a escala atual, nao mudaria a estrutura base. Mudaria antes a modelagem de `ActionPlan` e historico de classificacao:

```text
accounts/{account_id}/action_plans/{action_plan_id}
accounts/{account_id}/emails/{message_id}/classification_history/{classification_id}
```

Ou manteria `classifications/{message_id}` como estado atual e adicionaria historico apenas quando IA ou reclassificacao virarem reais.

### Risco de custo elevado

Baixo em 0.1. Medio ao escalar para muitas contas porque cada e-mail gera multiplas escritas:

- email;
- classification;
- possivelmente action_plan;
- run.

O custo cresce linearmente com mensagens processadas, mas o risco maior e reprocessar sempre os mesmos ultimos N e-mails sem janela incremental eficiente.

### Risco de consultas lentas

Baixo para acessos por documento. Medio para dashboards futuros, porque os dados estao em subcolecoes por conta e nao ha read model agregado. Consultas cross-account exigirao collection group queries e indices.

## 5. Cloud Run

### Adequacao atual

Cloud Run Job e adequado para Release 0.1. O processamento e batch, sem necessidade de servidor sempre ativo. O custo operacional tende a ser baixo e o modelo simplifica deploy e smoke.

### Riscos

- Cold start nao e problema relevante em job diario, mas importa para smoke e diagnostico.
- A execucao sequencial pode aumentar duracao conforme contas crescem.
- O report final e mantido em memoria. Com muitos itens, isso vira problema.
- Logs com JSON final indentado podem truncar/fragmentar, como ja aconteceu.
- O Makefile cria/atualiza o job com variaveis legadas `GOOGLE_CLIENT_SECRET_NAME` e `GOOGLE_REFRESH_TOKEN_NAME`, enquanto o app usa `accounts.yaml` e `secret_prefix`. Isso nao quebra, mas confunde.

### O que mudaria futuramente

- Parametrizar job por `ACCOUNT_ID` ou shard quando houver muitas contas.
- Definir timeout e memoria explicitamente conforme metricas reais.
- Reduzir tamanho do report nos logs e persistir report completo no Firestore.
- Adicionar Cloud Scheduler apenas quando a notificacao diaria tiver valor validado.
- Criar metricas por run e por conta antes de aumentar volume.

## 6. Seguranca

### OAuth

Risco medio. O runtime usa `gmail.modify` e `calendar.events`, apesar de operar como read-only. A justificativa de compatibilidade com refresh token e valida, mas o estado ideal e rotacionar token para escopos minimos assim que possivel.

Problema mais objetivo: `scripts/google_oauth_local.py` ainda gera token com `gmail.readonly`, divergente do runtime. Isso pode produzir tokens que falham em producao.

### Secret Manager

Uso correto para client secret e refresh token. Riscos:

- `doctor.py` espera somente secrets da conta `google-pessoal`, nao valida dinamicamente todos os `secret_prefix` habilitados em `accounts.yaml`.
- Nao ha verificacao de versao, idade ou rotacao de secrets.
- Nao ha politica documentada de revogacao de refresh token.

### IAM e Service Account

Documentacao recomenda menor privilegio, mas nao ha evidencia no codigo de validacao granular de roles. `doctor.py` valida existencia de recursos, nao permissoes minimas. Isso e suficiente para 0.1, insuficiente para 1.0.

### Firestore

Risco baixo no codigo, medio no produto. O service account provavelmente precisa de acesso de escrita amplo no banco. Para 1.0, vale limitar por projeto/ambiente e registrar uma politica de dados pessoais.

### Cloud Build e Docker

Dockerfile e simples. Risco principal:

- imagem instala dependencias de teste (`pytest`) em runtime;
- nao ha usuario non-root definido;
- nao ha pin de digest da imagem base;
- nao ha separacao clara entre dependencias runtime e dev.

Nada disso bloqueia 0.1, mas deve ser tratado antes de producao mais seria.

### Dados pessoais versionados

`config/accounts.yaml` contem e-mail pessoal real. Mesmo sem segredo, isso e dado pessoal e deve sair do repositorio ou ser substituido por exemplo. Para produto de longo prazo, arquivos reais de configuracao devem ser gerados por ambiente ou mantidos fora do git.

## 7. Engenharia

### Estrutura de pastas

Boa para a fase atual:

```text
app/core
app/connectors
app/storage
scripts
config
docs
tests
```

O ponto de atencao e que `core` ainda contem conceitos de e-mail no protocolo principal. Conforme surgirem outros dominios, sera preciso separar contratos genericos de contratos de e-mail.

### Legibilidade

Boa. O codigo e direto, com poucos niveis de indirecao. Isso e uma vantagem competitiva para manutencao.

### Testes

Fortes para 0.1. Cobrem:

- AccountManager;
- ConnectorManager;
- DailyJob;
- Classifier;
- Persistence;
- AutomationPlanner;
- Reporter;
- smoke e doctor.

Lacunas:

- poucos testes de falha parcial no `DailyJob`;
- nenhum teste de multiplas contas com uma conta falhando e outra seguindo;
- poucos testes de quotas, timeouts ou retry;
- `GmailConnector.fetch_recent` nao tem teste completo de paginacao/list/get com service fake;
- classificacao baseada em regras precisa de mais casos negativos reais;
- persistencia nao testa tipos reais do Firestore nem timestamps serializaveis em ambiente real.

### Observabilidade

Suficiente para 0.1, fraca para 1.0:

- logs nao sao estruturados em JSON;
- nao ha `run_id` criado no inicio e propagado;
- erros sao agregados no report, mas nem todos os passos tem contexto uniforme;
- nao ha metricas exportadas;
- nao ha severidade padronizada por componente.

### Tratamento de erros

`DailyJob` isola falha por conta, o que e bom. Mas nao existe classificacao de erros recuperaveis, retry, backoff ou erro por etapa. Para poucas contas isso e aceitavel; para escala maior, falhas externas vao dominar.

### Onboarding

Bom, com runbook e backlog. O problema e excesso de documentos com sobreposicao: `ARCHITECTURE.md`, `MASTER_ARCHITECTURE.md`, `NEXT_STEPS.md`, `BACKLOG.md` e `CODEX_TASKS.md` repetem informacoes e podem divergir.

## 8. Roadmap ate 1.0 por releases

### Release 0.2 - Hardening operacional e contratos atuais

Objetivo: tornar a base atual confiavel antes de adicionar provedores.

Funcionalidades:

- alinhar OAuth local com runtime;
- remover dados pessoais versionados;
- tornar `doctor` dinamico por `accounts.yaml`;
- tornar `smoke` multi-conta ou parametrizado por conta;
- adicionar `run_id` no inicio da execucao e propagar para logs, emails, classifications e action_plans;
- registrar arquitetura atual versus arquitetura futura sem ambiguidade.

Dependencias:

- Release 0.1;
- Cloud Shell validado.

Complexidade: baixa a media.

Riscos:

- mexer em OAuth pode exigir rotacao de token;
- ajustes de smoke podem tocar operacao em Cloud Shell.

Criterios para concluir:

- `make release` passa;
- docs refletem somente o estado real;
- nenhuma conta real fica versionada;
- run_id aparece em logs e Firestore.

### Release 0.3 - Multi-conta real

Objetivo: provar que adicionar contas via YAML funciona operacionalmente.

Funcionalidades:

- validar secrets por conta habilitada;
- processar multiplas contas Gmail;
- report por conta com falha parcial;
- limites por conta;
- testes de uma conta falhar sem abortar as demais;
- smoke parametrizavel por conta ou validacao agregada.

Dependencias:

- doctor dinamico;
- run_id.

Complexidade: media.

Riscos:

- quotas Gmail;
- confusao de secrets;
- custo Firestore maior.

Criterios para concluir:

- duas contas Gmail habilitadas funcionam sem mudanca de codigo;
- falha de uma conta aparece no report sem impedir outra;
- Firestore separa corretamente subcolecoes por account_id.

### Release 0.4 - Contrato generico de itens e ActionPlan auditavel

Objetivo: preparar o core para Calendar, WhatsApp e IA sem forcar tudo em e-mail.

Funcionalidades:

- decidir formalmente se `WorkItem` entra no pipeline real agora;
- definir `DomainItem` ou `ConnectorResult`;
- tornar `ActionPlan` uma entidade com id, created_at, source item e status;
- manter compatibilidade com Firestore atual ou documentar migracao leve;
- versionar classificacoes.

Dependencias:

- multi-conta real;
- ADR sobre contrato de connector generico.

Complexidade: media.

Riscos:

- refatoracao do pipeline;
- migracao de dados existentes.

Criterios para concluir:

- pipeline real e documentado convergem;
- ActionPlan pode ser consultado por status/tipo;
- nenhuma integracao externa nova foi necessaria para validar.

### Release 0.5 - Outlook Email

Objetivo: provar que o core aceita outro provedor de e-mail.

Funcionalidades:

- definir secrets Microsoft;
- implementar OutlookConnector;
- normalizar para `EmailEntity`;
- registrar provider no ConnectorManager;
- testes de normalizacao;
- conta Outlook desabilitada por padrao;
- smoke em DRY_RUN.

Dependencias:

- contrato de connector de e-mail estabilizado;
- secrets por conta.

Complexidade: media a alta.

Riscos:

- OAuth Microsoft;
- diferenças de threading, categorias e headers;
- quotas Graph API.

Criterios para concluir:

- Gmail e Outlook processam no mesmo pipeline;
- DailyJob nao muda para suportar Outlook;
- Firestore separa provider e account_id corretamente.

### Release 0.6 - Resumo diario sem envio real

Objetivo: entregar valor de produto sem ainda depender de WhatsApp real.

Funcionalidades:

- gerar resumo textual a partir do report;
- priorizar itens por categoria e prioridade;
- salvar resumo no Firestore;
- incluir erros e avisos operacionais;
- manter DRY_RUN.

Dependencias:

- ActionPlan auditavel;
- report confiavel.

Complexidade: media.

Riscos:

- resumo ruim por falta de contexto;
- excesso de ruido.

Criterios para concluir:

- resumo diario e util em logs/Firestore;
- nao envia mensagem externa;
- cobre Gmail e Outlook quando ambos existirem.

### Release 0.7 - WhatsApp Notifier em DRY_RUN e depois envio controlado

Objetivo: criar canal de entrega do resumo diario.

Funcionalidades:

- `NotificationEntity`;
- interface de notifier;
- WhatsAppNotifier com modo dry-run;
- templates e secrets documentados;
- envio real apenas com flag explicita e allowlist.

Dependencias:

- resumo diario;
- politica de seguranca para acoes externas.

Complexidade: media.

Riscos:

- configuracao Meta;
- templates aprovados;
- custo e limites de envio;
- risco de enviar dados sensiveis.

Criterios para concluir:

- DRY_RUN mostra payload sem envio;
- envio real testado com numero controlado;
- logs e Firestore registram notification status.

### Release 0.8 - Google Calendar read-only

Objetivo: enriquecer contexto com agenda sem criar eventos automaticamente.

Funcionalidades:

- CalendarConnector read-only;
- `CalendarEventEntity`;
- deteccao de conflitos simples;
- associacao de e-mails com possiveis eventos;
- planos de acao de revisao.

Dependencias:

- contrato generico de itens;
- politica OAuth revisada.

Complexidade: media.

Riscos:

- escopos Calendar atuais sao mutaveis;
- risco de misturar Gmail e Calendar no mesmo conector;
- timezone e recorrencia.

Criterios para concluir:

- agenda lida sem mutacao;
- eventos normalizados;
- report mostra conflitos ou proximos compromissos.

### Release 0.9 - IA assistiva com baixo risco

Objetivo: melhorar classificacao e resumo sem entregar controle de acoes a IA.

Funcionalidades:

- `LLMProvider`;
- provider fake para testes;
- prompt policy;
- uso apenas para classificacao/refino/resumo;
- cache de respostas;
- limites de custo;
- logs sem dados sensiveis desnecessarios.

Dependencias:

- WorkItem ou contrato equivalente real;
- classificacao versionada;
- resumo diario.

Complexidade: alta.

Riscos:

- custo;
- privacidade;
- alucinacao;
- prompts instaveis;
- dependência de provider.

Criterios para concluir:

- fallback para regras funciona;
- IA nao executa acoes;
- custo por run e registrado;
- resultados podem ser auditados.

### Release 1.0 - Produto diario confiavel

Objetivo: operar diariamente com valor real, seguranca e auditabilidade.

Funcionalidades:

- Gmail e Outlook funcionais;
- Calendar read-only;
- resumo diario por WhatsApp;
- Scheduler diario;
- ActionPlans auditaveis;
- report persistido;
- doctor/smoke/release confiaveis;
- documentacao operacional enxuta;
- politica de dados e seguranca.

Dependencias:

- releases anteriores;
- validacao por 7 dias consecutivos.

Complexidade: alta.

Riscos:

- confiabilidade das APIs externas;
- credenciais expiradas;
- excesso de ruido no resumo;
- custo de Firestore/logs/IA;
- privacidade.

Criterios para concluir:

- 7 execucoes diarias seguidas sem erro critico;
- WhatsApp entrega resumo util;
- nenhuma acao mutavel ocorre sem autorizacao;
- smoke e doctor detectam falhas reais;
- documentacao permite onboarding de novo desenvolvedor.

## 9. Priorizacao

Eu nao manteria Outlook como a proxima Release imediata se a pergunta for "qual deve ser a Release 0.2". Eu colocaria antes uma release curta de hardening operacional e contratos atuais.

Justificativa tecnica:

- Outlook e a melhor proxima integracao para provar multi-provider, mas hoje o contrato de connector ainda e email-specific e o `WorkItem` nao participa do fluxo real.
- O smoke e o doctor ainda tem partes amarradas a `pessoal_google` e secrets fixos.
- Ha divergencia real de OAuth entre script local e runtime.
- Ha dado pessoal versionado.
- Sem `run_id` propagado, debugar multi-conta e multi-provider ficara mais dificil.

Depois dessa Release 0.2 de consolidacao, Outlook deve sim ser a proxima integracao. Ele e tecnicamente melhor que WhatsApp e Calendar como proximo passo porque:

- valida a premissa de multiplos provedores de e-mail;
- reaproveita `EmailEntity`;
- testa `ConnectorManager` sem introduzir novo dominio;
- entrega valor direto na triagem.

## 10. Divida tecnica

### Critica

- Divergencia de escopos entre `scripts/google_oauth_local.py` e `GmailConnector`.
- Dados pessoais em `config/accounts.yaml` versionado.
- `ActionPlan` sem identidade propria para futura execucao auditavel.

### Alta

- `WorkItem` documentado como contrato central, mas nao usado no pipeline real.
- `ConnectorManagerProtocol` retorna `list[EmailEntity]`, insuficiente para Calendar/WhatsApp/Drive.
- `doctor.py` valida secrets fixos, nao todas as contas habilitadas.
- `smoke.py` tem fallback padrao para uma conta especifica.
- Falta `run_id` criado no inicio e propagado.
- Falta politica clara de retry/backoff para APIs externas.
- Falta historico/versionamento de classificacoes.

### Media

- Logs nao estruturados.
- Docker inclui dependencias de teste no runtime.
- Docker roda como root.
- `FirestoreStore` e alias sem valor funcional.
- Documentacao sobre sprints antigas e estado atual esta misturada.
- Configuracao possui campos futuros (`calendar.enabled`) que nao tem efeito real.
- `AccountPolicies` fala em mark_read, mas nao ha executor real.
- Falta estrategia de retencao de dados.
- Falta teste completo de `GmailConnector.fetch_recent`.

### Baixa

- Alguns nomes ainda refletem sprint e nao produto.
- `max_emails_per_provider` em Settings parece pouco usado frente a `account.max_emails`.
- `msal` ja esta em requirements antes do Outlook existir.
- `python-dotenv` esta em requirements, mas nao aparece usado no codigo atual.

## 11. Recomendacoes

### 1. Alinhar OAuth local e runtime

Descricao: corrigir a divergencia entre escopos usados para gerar refresh token e escopos usados no runtime.  
Impacto: reduz falhas `invalid_scope` e simplifica operacao.  
Esforco: baixo.  
Release ideal: 0.2.

### 2. Remover dados pessoais versionados

Descricao: substituir `config/accounts.yaml` real por exemplo anonimo ou manter arquivo real fora do git.  
Impacto: reduz risco de privacidade e melhora disciplina de configuracao.  
Esforco: baixo.  
Release ideal: 0.2.

### 3. Tornar doctor e smoke orientados por accounts.yaml

Descricao: validar secrets e Firestore para todas as contas habilitadas, nao apenas `pessoal_google`.  
Impacto: torna multi-conta confiavel.  
Esforco: medio.  
Release ideal: 0.2 ou 0.3.

### 4. Propagar run_id

Descricao: criar `run_id` no inicio do `DailyJob` e persistir em logs, emails, classifications, action_plans e report.  
Impacto: melhora debug, auditoria e correlacao operacional.  
Esforco: medio.  
Release ideal: 0.2.

### 5. Formalizar contrato generico antes de Calendar/WhatsApp

Descricao: decidir se o pipeline recebe `WorkItem`, `DomainItem` ou `ConnectorResult`, e fazer o codigo refletir isso.  
Impacto: evita retrabalho ao adicionar dominios nao-email.  
Esforco: medio.  
Release ideal: 0.4.

### 6. Transformar ActionPlan em entidade auditavel

Descricao: adicionar identidade, timestamps, origem e status por plano antes de executor real.  
Impacto: prepara automacao segura, retries e aprovacoes.  
Esforco: medio.  
Release ideal: 0.4.

### 7. Criar logs estruturados minimos

Descricao: padronizar logs com `run_id`, `account_id`, `provider`, `component`, `event`, `duration_ms` e `error_type`.  
Impacto: reduz tempo de diagnostico em Cloud Run.  
Esforco: medio.  
Release ideal: 0.3.

### 8. Adicionar testes de falha parcial multi-conta

Descricao: garantir que falha em uma conta nao impede outra e aparece no report.  
Impacto: aumenta confianca antes de Outlook.  
Esforco: baixo.  
Release ideal: 0.3.

### 9. Definir retencao e historico

Descricao: decidir por quanto tempo manter emails, classificacoes, action plans e runs.  
Impacto: controla custo e privacidade.  
Esforco: baixo a medio.  
Release ideal: 0.5.

### 10. Separar dependencias runtime e dev

Descricao: remover dependencias de teste da imagem de producao ou criar requirements separados.  
Impacto: reduz superficie e tamanho da imagem.  
Esforco: baixo.  
Release ideal: antes de 1.0.

## 12. ADRs recomendados

### ADR - Contrato real de entrada do pipeline

Problema: documentos dizem que `WorkItem` e central, mas o codigo processa `EmailEntity` diretamente.  
Alternativas:

- manter `EmailEntity` ate Outlook e adiar `WorkItem`;
- inserir `WorkItem` agora no pipeline;
- criar `ConnectorResult` como camada intermediaria.

Decisao recomendada: adiar para Release 0.4, mas registrar explicitamente que 0.1 e 0.3 sao email-first.  
Consequencias: evita refatoracao prematura, mas impede Calendar/WhatsApp antes da decisao.

### ADR - Modelagem de ActionPlan

Problema: `ActionPlan` atual e salvo agregado por mensagem, sem identidade propria.  
Alternativas:

- manter por `message_id`;
- criar documento por plano;
- criar subcolecao por e-mail.

Decisao recomendada: documento por plano em `accounts/{account_id}/action_plans/{action_plan_id}` antes de executor real.  
Consequencias: melhora consulta, status, retry e auditoria, com pequeno aumento de escritas.

### ADR - Politica de OAuth e escopos minimos

Problema: runtime usa escopos mais amplos por compatibilidade.  
Alternativas:

- manter escopos atuais indefinidamente;
- rotacionar imediatamente;
- manter temporariamente e definir prazo de rotacao.

Decisao recomendada: manter temporariamente, alinhar script local e planejar rotacao para escopo minimo.  
Consequencias: reduz incidente operacional agora e melhora seguranca depois.

### ADR - Estrategia de escala por lotes

Problema: job unico sequencial nao escala para centenas ou milhares de contas.  
Alternativas:

- manter job unico;
- particionar por account_id;
- particionar por shards configurados.

Decisao recomendada: manter job unico ate dezenas de contas, introduzir shard parametrizado antes de 100 contas ativas.  
Consequencias: preserva simplicidade e cria caminho claro de crescimento.

### ADR - Retencao de dados pessoais

Problema: Firestore acumulara e-mails, headers, snippets e classificacoes.  
Alternativas:

- manter tudo indefinidamente;
- apagar apos janela fixa;
- agregar e arquivar detalhes antigos.

Decisao recomendada: definir politica simples por tipo de dado antes de WhatsApp e IA.  
Consequencias: reduz custo, risco de privacidade e volume de consultas.

## 13. Veredito arquitetural

A Release 0.1 esta aprovada como base funcional e operacional. A arquitetura atual e correta para o tamanho do produto e nao deve ser substituida por Kubernetes, microservicos, mensageria distribuida ou Event Bus.

O risco nao esta na escolha de tecnologia. O risco esta em acelerar integracoes antes de estabilizar contratos e operacao multi-conta. A melhor evolucao ate 1.0 e incremental:

1. endurecer operacao e seguranca;
2. provar multi-conta;
3. formalizar contratos genericos;
4. adicionar Outlook;
5. entregar resumo;
6. adicionar WhatsApp;
7. adicionar Calendar;
8. adicionar IA com controle.

Essa ordem preserva simplicidade, reduz custo operacional e evita que o projeto vire um conjunto de conectores acoplados por pressa.
