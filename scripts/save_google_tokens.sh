#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-agenda-pessoal-projeto}"
CLIENT_FILE="${CLIENT_FILE:-client_secret.json}"
SECRET_PREFIX="${SECRET_PREFIX:-google-pessoal}"

if [[ -z "${GOOGLE_REFRESH_TOKEN:-}" ]]; then
  echo "Defina GOOGLE_REFRESH_TOKEN antes de rodar."
  exit 1
fi

if [[ ! -f "$CLIENT_FILE" ]]; then
  echo "Arquivo nao encontrado: $CLIENT_FILE"
  exit 1
fi

printf '%s' "$(cat "$CLIENT_FILE")" | gcloud secrets create "${SECRET_PREFIX}-client-secret-json" --project "$PROJECT_ID" --data-file=- 2>/dev/null || \
printf '%s' "$(cat "$CLIENT_FILE")" | gcloud secrets versions add "${SECRET_PREFIX}-client-secret-json" --project "$PROJECT_ID" --data-file=-

printf '%s' "$GOOGLE_REFRESH_TOKEN" | gcloud secrets create "${SECRET_PREFIX}-refresh-token" --project "$PROJECT_ID" --data-file=- 2>/dev/null || \
printf '%s' "$GOOGLE_REFRESH_TOKEN" | gcloud secrets versions add "${SECRET_PREFIX}-refresh-token" --project "$PROJECT_ID" --data-file=-

echo "Google tokens gravados no Secret Manager."
