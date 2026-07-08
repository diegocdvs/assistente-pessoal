from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass


REQUIRED_APIS = (
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
    "gmail.googleapis.com",
)
REQUIRED_SECRETS = (
    "google-pessoal-client-secret-json",
    "google-pessoal-refresh-token",
)
EXPECTED_PROJECT_ID = "agenda-pessoal-projeto"
EXPECTED_REGION = "southamerica-east1"


@dataclass
class CheckSummary:
    ok: int = 0
    warn: int = 0
    error: int = 0

    def add(self, status: str) -> None:
        if status == "OK":
            self.ok += 1
        elif status == "WARN":
            self.warn += 1
        else:
            self.error += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico operacional do Assistente Pessoal.")
    parser.add_argument("--project-id", default=EXPECTED_PROJECT_ID)
    parser.add_argument("--region", default=EXPECTED_REGION)
    parser.add_argument("--job-name", default="assistente-pessoal-diario")
    args = parser.parse_args()

    summary = CheckSummary()

    print("== Ambiente ==")
    record(summary, "OK", f"Python instalado: {sys.version.split()[0]}")
    check_command(summary, "pip", [sys.executable, "-m", "pip", "--version"])
    check_venv(summary)
    check_executable(summary, "Docker instalado", "docker", ["docker", "--version"])
    check_executable(summary, "gcloud instalado", "gcloud", ["gcloud", "--version"])
    check_gcloud_auth(summary)

    print("\n== Projeto ==")
    check_expected_value(summary, "Projeto esperado", args.project_id, EXPECTED_PROJECT_ID)
    check_expected_value(summary, "Regiao esperada", args.region, EXPECTED_REGION)
    check_gcloud_config(summary, "Projeto ativo no gcloud", "core/project", EXPECTED_PROJECT_ID)
    check_gcloud_region(summary, args.region)

    print("\n== APIs ==")
    for api in REQUIRED_APIS:
        check_api(summary, args.project_id, api)

    print("\n== Secret Manager ==")
    for secret in REQUIRED_SECRETS:
        check_secret(summary, args.project_id, secret)

    print("\n== Cloud Run ==")
    check_job(summary, args.project_id, args.region, args.job_name)

    print("\n== Resumo ==")
    print(f"[OK] {summary.ok} checks")
    print(f"[WARN] {summary.warn} checks")
    print(f"[ERROR] {summary.error} checks")
    return 1 if summary.error else 0


def record(summary: CheckSummary, status: str, message: str) -> None:
    summary.add(status)
    print(f"[{status}] {message}")


def run(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout)


def check_command(summary: CheckSummary, label: str, command: list[str]) -> None:
    try:
        result = run(command)
    except Exception as exc:
        record(summary, "ERROR", f"{label}: {exc}")
        return
    if result.returncode == 0:
        record(summary, "OK", f"{label}: {first_line(result.stdout)}")
    else:
        record(summary, "ERROR", f"{label}: {first_line(result.stderr) or 'falhou'}")


def check_venv(summary: CheckSummary) -> None:
    if os.environ.get("VIRTUAL_ENV"):
        record(summary, "OK", f"Ambiente virtual ativo: {os.environ['VIRTUAL_ENV']}")
    else:
        record(summary, "WARN", "Ambiente virtual .venv nao parece estar ativo.")


def check_executable(summary: CheckSummary, label: str, executable: str, command: list[str]) -> None:
    if shutil.which(executable) is None:
        record(summary, "ERROR", f"{label}: comando '{executable}' nao encontrado.")
        return
    check_command(summary, label, command)


def check_gcloud_auth(summary: CheckSummary) -> None:
    if shutil.which("gcloud") is None:
        record(summary, "ERROR", "Autenticacao gcloud: gcloud nao encontrado.")
        return
    result = run(["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"])
    account = result.stdout.strip()
    if result.returncode == 0 and account:
        record(summary, "OK", f"Autenticacao gcloud ativa: {account}")
    else:
        record(summary, "ERROR", "Autenticacao gcloud valida nao encontrada.")


def check_expected_value(summary: CheckSummary, label: str, actual: str, expected: str) -> None:
    if actual == expected:
        record(summary, "OK", f"{label}: {actual}")
    else:
        record(summary, "ERROR", f"{label}: esperado {expected}, recebido {actual}")


def check_gcloud_config(summary: CheckSummary, label: str, key: str, expected: str) -> None:
    result = run(["gcloud", "config", "get-value", key, "--quiet"])
    value = result.stdout.strip()
    if result.returncode == 0 and value == expected:
        record(summary, "OK", f"{label}: {value}")
    else:
        record(summary, "ERROR", f"{label}: esperado {expected}, atual {value or 'nao definido'}")


def check_gcloud_region(summary: CheckSummary, expected_region: str) -> None:
    configured = []
    for key in ("run/region", "compute/region"):
        result = run(["gcloud", "config", "get-value", key, "--quiet"])
        value = result.stdout.strip()
        if result.returncode == 0 and value and value != "(unset)":
            configured.append((key, value))
    if not configured:
        record(summary, "WARN", f"Regiao gcloud nao definida; Makefile usara {expected_region}.")
        return
    wrong = [f"{key}={value}" for key, value in configured if value != expected_region]
    if wrong:
        record(summary, "ERROR", "Regiao gcloud diferente do esperado: " + ", ".join(wrong))
    else:
        record(summary, "OK", f"Regiao gcloud: {expected_region}")


def check_api(summary: CheckSummary, project_id: str, api: str) -> None:
    result = run([
        "gcloud",
        "services",
        "list",
        "--enabled",
        "--project",
        project_id,
        f"--filter=config.name:{api}",
        "--format=value(config.name)",
    ])
    if result.returncode == 0 and api in result.stdout.split():
        record(summary, "OK", f"API habilitada: {api}")
    else:
        record(summary, "ERROR", f"API nao habilitada ou inacessivel: {api}")


def check_secret(summary: CheckSummary, project_id: str, secret: str) -> None:
    result = run(["gcloud", "secrets", "describe", secret, "--project", project_id, "--format=value(name)"])
    if result.returncode == 0:
        record(summary, "OK", f"Secret existe: {secret}")
    else:
        record(summary, "ERROR", f"Secret ausente ou inacessivel: {secret}")


def check_job(summary: CheckSummary, project_id: str, region: str, job_name: str) -> None:
    result = run([
        "gcloud",
        "run",
        "jobs",
        "describe",
        job_name,
        "--project",
        project_id,
        "--region",
        region,
        "--format=value(metadata.name)",
    ])
    if result.returncode == 0 and result.stdout.strip() == job_name:
        record(summary, "OK", f"Cloud Run Job existe: {job_name}")
    else:
        record(summary, "ERROR", f"Cloud Run Job ausente ou inacessivel: {job_name}")


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


if __name__ == "__main__":
    raise SystemExit(main())
