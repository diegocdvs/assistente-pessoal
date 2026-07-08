# Engineering Playbook — Assistente Pessoal

## 1. Papéis

### ChatGPT

Responsável por:

- arquitetura;
- planejamento;
- backlog;
- critérios de aceite;
- revisão técnica;
- diagnóstico;
- documentação estratégica;
- prompts enxutos para o Codex.

### Codex

Responsável por:

- implementação;
- refatoração;
- testes;
- documentação técnica localizada;
- abertura de PRs ou commits pequenos.

### Usuário

Responsável por:

- executar comandos no Cloud Shell;
- validar telas e permissões externas;
- tomar decisões de produto;
- aprovar merges quando necessário.

## 2. Fluxo padrão de trabalho

```text
Especificação
↓
Task pequena
↓
Codex implementa
↓
Testes locais
↓
Review
↓
Merge
↓
Deploy
↓
Smoke test
↓
Validação Firestore/logs
```

## 3. Regra para uso do Codex

Codex é tratado como recurso limitado.

Cada prompt deve:

- ter escopo único;
- evitar repetir arquitetura inteira;
- referenciar `docs/MASTER_ARCHITECTURE.md`, `docs/NORTH_STAR.md` e `docs/PRD.md`;
- conter critérios de aceite;
- conter comandos de validação;
- proibir mudanças fora do escopo.

## 4. Definition of Done

Uma task só está concluída se:

1. código está versionado;
2. testes passam;
3. `python -m compileall app scripts` passa;
4. README/docs foram atualizados quando necessário;
5. não há credenciais versionadas;
6. `DRY_RUN` foi respeitado;
7. deploy passa, se a task afetar runtime;
8. smoke test passa, se a task afetar execução;
9. logs não mostram erros críticos.

## 5. Comandos padrão

### Validação local

```bash
source .venv/bin/activate
python -m pytest
python -m compileall app scripts
```

### Deploy

```bash
git checkout main
git pull
make deploy
make run-job
```

### Logs

```bash
gcloud beta run jobs executions logs read NOME_DA_EXECUCAO --region southamerica-east1
```

### Verificação Firestore

```bash
python - <<'PY'
from google.cloud import firestore

PROJECT_ID = "agenda-pessoal-projeto"
ACCOUNT_ID = "pessoal_google"

db = firestore.Client(project=PROJECT_ID)
for sub in ["emails", "classifications", "action_plans"]:
    docs = list(db.collection("accounts").document(ACCOUNT_ID).collection(sub).limit(5).stream())
    print(sub, len(docs))
    for doc in docs:
        print(" -", doc.id)
PY
```

## 6. Política de branches

- `main`: sempre deployável.
- `sprint-x-y-*`: branches de sprint.
- `task-x-y-*`: branches menores quando necessário.

Preferência:

- uma task por commit ou poucos commits coesos;
- PRs pequenos;
- merge somente após validação.

## 7. Política para infraestrutura

Não alterar infraestrutura durante task funcional, salvo necessidade explícita.

Mudanças em:

- Cloud Run;
- IAM;
- Secret Manager;
- OAuth;
- APIs GCP;
- Scheduler;
- Artifact Registry;

exigem seção de risco e validação própria.

## 8. Política para segurança

Proibido versionar:

- `.env`;
- `client_secret.json`;
- refresh tokens;
- arquivos de credenciais;
- dumps com dados sensíveis.

## 9. Políticas de DRY_RUN

Enquanto `DRY_RUN=true`, é proibido:

- marcar e-mail como lido;
- arquivar;
- mover;
- excluir;
- criar evento;
- enviar WhatsApp real;
- executar qualquer ação externa mutável.

Apenas leitura, persistência, classificação, relatório e planejamento são permitidos.

## 10. Ordem atual de sprints

1. Sprint 1.6 — Operação mínima.
2. Sprint 2 — OutlookConnector.
3. Sprint 3 — WhatsAppNotifier.
4. Sprint 4 — Calendar Intelligence.
5. Sprint 5 — LLM Provider.
6. Sprint 6 — Dashboard.

## 11. Formato padrão de prompt para Codex

```text
Implemente a Task X.Y seguindo:
- docs/NORTH_STAR.md
- docs/MASTER_ARCHITECTURE.md
- docs/PRD.md
- docs/ENGINEERING_PLAYBOOK.md

Escopo:
...

Fora de escopo:
...

Critérios de aceite:
...

Validação:
python -m pytest
python -m compileall app scripts

Não alterar:
...
```
