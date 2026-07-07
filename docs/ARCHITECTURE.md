# Arquitetura do Assistente Pessoal

## Objetivo

Construir um assistente pessoal hospedado no Google Cloud, capaz de processar múltiplas caixas de e-mail, classificar mensagens, detectar eventos, registrar histórico e enviar relatórios.

## Princípios

1. O computador local é usado apenas para configuração, desenvolvimento e autorização OAuth inicial.
2. A execução diária acontece no Google Cloud, sem depender do PC ligado.
3. O sistema deve aceitar múltiplas contas desde o início.
4. Ações destrutivas ou arriscadas ficam bloqueadas em modo seguro até validação.
5. Regras explícitas têm prioridade sobre IA.
6. IA entra apenas quando regras não forem suficientes.

## Fluxo de execução

```text
Cloud Scheduler
  -> Cloud Run Job
    -> Carrega contas ativas
    -> Lê Gmail e Outlook por conta
    -> Classifica e-mails
    -> Detecta eventos
    -> Simula ou executa ações
    -> Salva histórico no Firestore
    -> Envia relatório por WhatsApp
```

## Multi-contas

Cada caixa de e-mail é tratada como uma conta configurável.

Exemplos:

- `pessoal_google`: Gmail pessoal.
- `profissional_google`: Gmail profissional.
- `profissional_outlook`: Outlook profissional.

Cada conta possui:

- identificador lógico;
- provedor;
- endereço de e-mail;
- segredo OAuth próprio no Secret Manager;
- regras específicas;
- política de leitura/marcação.

## Coleções Firestore previstas

```text
accounts/          Contas conectadas
rules/             Regras globais e por conta
runs/              Execuções da rotina
processed_emails/  Histórico de e-mails processados
events/            Eventos detectados ou criados
alerts/            Alertas relevantes
settings/          Configurações gerais
```

## Política de segurança

No `DRY_RUN=true`, o sistema pode:

- ler mensagens;
- classificar;
- registrar relatório;
- simular ações.

No `DRY_RUN=true`, o sistema não pode:

- marcar como lido;
- arquivar;
- apagar;
- criar evento;
- enviar mensagem externa, salvo teste explícito.

## Criticidade

- `critica`: alerta imediato.
- `importante`: entra no relatório diário.
- `informativa`: fica registrada.
- `ruido`: publicidade, newsletter e baixa relevância.
