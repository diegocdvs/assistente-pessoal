from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
]


def resolve_gcloud() -> str:
    candidates = [
        shutil.which("gcloud"),
        shutil.which("gcloud.cmd"),
        r"C:\Users\Diego\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("gcloud não encontrado. Abra o terminal 'Google Cloud SDK Shell' ou adicione gcloud ao PATH.")


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True)


def save_secret(project_id: str, secret_name: str, value: str) -> None:
    gcloud = resolve_gcloud()

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as temp:
        temp.write(value)
        temp_path = Path(temp.name)

    try:
        create_cmd = [
            gcloud, "secrets", "create", secret_name,
            "--project", project_id,
            f"--data-file={temp_path}",
        ]
        add_version_cmd = [
            gcloud, "secrets", "versions", "add", secret_name,
            "--project", project_id,
            f"--data-file={temp_path}",
        ]

        result = run_command(create_cmd)
        if result.returncode != 0:
            result = run_command(add_version_cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Falha ao salvar secret: {secret_name}")
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera refresh token Google localmente.")
    parser.add_argument("--client-secret-file", required=True)
    parser.add_argument("--project-id", default="agenda-pessoal-projeto")
    parser.add_argument("--secret-prefix", default="google-pessoal")
    args = parser.parse_args()

    client_secret_path = Path(args.client_secret_file)
    if not client_secret_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {client_secret_path}")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), scopes=SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        raise RuntimeError("Refresh token não gerado. Revogue consentimentos antigos e rode novamente.")

    print("\nGOOGLE_REFRESH_TOKEN=")
    print(creds.refresh_token)

    answer = input("\nSalvar automaticamente no Google Secret Manager? [S/N]: ").strip().lower()
    if answer not in {"s", "sim", "y", "yes"}:
        print("OK. Token não salvo automaticamente.")
        return

    client_secret_json = client_secret_path.read_text(encoding="utf-8")
    save_secret(args.project_id, f"{args.secret_prefix}-client-secret-json", client_secret_json)
    save_secret(args.project_id, f"{args.secret_prefix}-refresh-token", creds.refresh_token)

    print("\nSecrets salvos com sucesso:")
    print(f"- {args.secret_prefix}-client-secret-json")
    print(f"- {args.secret_prefix}-refresh-token")


if __name__ == "__main__":
    main()
