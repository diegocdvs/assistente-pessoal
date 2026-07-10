# Google Calendar Setup

## API

Habilite a Google Calendar API no projeto:

```bash
gcloud services enable calendar-json.googleapis.com
```

## Escopos OAuth read-only

Escopos minimos para a Release 0.8:

```text
https://www.googleapis.com/auth/calendar.events.readonly
https://www.googleapis.com/auth/calendar.calendarlist.readonly
```

Se o refresh token atual nao foi emitido com esses escopos, sera necessario reautorizar.

## Gerar refresh token

```bash
python scripts/google_oauth_local.py \
  --client-secret-file client_secret.json \
  --project-id agenda-pessoal-projeto \
  --secret-prefix google-pessoal \
  --include-calendar-readonly
```

O script mostra os escopos antes do consentimento e so grava no Secret Manager apos confirmacao explicita.

## Feature flag

Calendar permanece desligado por padrao:

```bash
CALENDAR_ENABLED=false
```

Para validar em ambiente controlado:

```bash
CALENDAR_ENABLED=true
CALENDAR_PROVIDER=google
CALENDAR_IDS=primary
CALENDAR_LOOKAHEAD_DAYS=7
CALENDAR_LOOKBACK_DAYS=1
CALENDAR_MAX_EVENTS=100
```

## Troubleshooting

`invalid_scope` ou `insufficientPermissions`:

- reautorize com os escopos read-only acima;
- atualize `<secret_prefix>-refresh-token`;
- confirme que a Calendar API esta habilitada.

## Validacao

```bash
make validate
make calendar
make double-check
```

Checklist:

- Calendar API habilitada;
- refresh token atualizado;
- `CALENDAR_ENABLED=true` somente no ambiente de teste;
- logs sem tokens, descricoes completas ou meeting URLs;
- nenhum evento criado, alterado ou excluido.
