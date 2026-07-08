from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any


FORBIDDEN_PATTERNS = (
    "invalid_scope",
    "accessNotConfigured",
    "RefreshError",
    "HttpError 403",
    "MVP placeholder ativo",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test operacional do Cloud Run Job.")
    parser.add_argument("--project-id", default="agenda-pessoal-projeto")
    parser.add_argument("--region", default="southamerica-east1")
    parser.add_argument("--job-name", default="assistente-pessoal-diario")
    args = parser.parse_args()

    print("== Executando job ==")
    run_job = run(["make", "run-job"])
    print(run_job.stdout, end="")
    print(run_job.stderr, end="", file=sys.stderr)
    if run_job.returncode != 0:
        print("[ERROR] make run-job falhou.")
        return run_job.returncode

    execution = find_execution_name(run_job.stdout + "\n" + run_job.stderr)
    if not execution:
        execution = latest_execution(args.project_id, args.region, args.job_name)
    if not execution:
        print("[ERROR] Nao foi possivel identificar a execucao do Cloud Run Job.")
        return 1
    print(f"[OK] Execucao: {execution}")

    print("\n== Lendo logs ==")
    logs_result = run([
        "gcloud",
        "beta",
        "run",
        "jobs",
        "executions",
        "logs",
        "read",
        execution,
        "--project",
        args.project_id,
        "--region",
        args.region,
    ])
    logs = logs_result.stdout + "\n" + logs_result.stderr
    print(logs)
    if logs_result.returncode != 0:
        print("[ERROR] Falha ao ler logs da execucao.")
        return logs_result.returncode

    for pattern in FORBIDDEN_PATTERNS:
        if pattern in logs:
            print(f"[ERROR] Padrao proibido encontrado nos logs: {pattern}")
            return 1

    report = find_report(logs)
    if report is None:
        print("[ERROR] Report final nao encontrado nos logs.")
        return 1

    errors = report.get("errors")
    if errors != []:
        print(f"[ERROR] Report possui erros: {errors}")
        return 1

    emails_processed = int(report.get("total") or 0)
    classifications = sum(int(value) for value in (report.get("total_by_category") or {}).values())
    action_plans = len(report.get("planned_actions") or [])
    duration = report.get("duration_seconds", "desconhecida")

    if emails_processed <= 0:
        print("[ERROR] Nenhum email processado.")
        return 1
    if classifications <= 0:
        print("[ERROR] Nenhuma classificacao encontrada no report.")
        return 1
    if action_plans <= 0:
        print("[ERROR] Nenhum action plan encontrado no report.")
        return 1

    firestore_status = validate_firestore(args.project_id, report)

    print("\n== Resumo smoke ==")
    print(f"execucao: {execution}")
    print(f"duracao: {duration}")
    print(f"emails processados: {emails_processed}")
    print(f"classificacoes: {classifications}")
    print(f"action plans: {action_plans}")
    print(f"firestore: {firestore_status}")
    print("status: OK")
    return 0


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True)


def find_execution_name(output: str) -> str | None:
    patterns = [
        r"Execution\s+\[([^\]]+)\]",
        r"executions/([a-zA-Z0-9_.-]+)",
        r"(assistente-pessoal-diario-[a-zA-Z0-9-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)
    return None


def latest_execution(project_id: str, region: str, job_name: str) -> str | None:
    result = run([
        "gcloud",
        "run",
        "jobs",
        "executions",
        "list",
        "--project",
        project_id,
        "--region",
        region,
        "--job",
        job_name,
        "--sort-by=~metadata.creationTimestamp",
        "--limit=1",
        "--format=value(metadata.name)",
    ])
    if result.returncode == 0:
        return result.stdout.strip() or None
    return None


def find_report(logs: str) -> dict[str, Any] | None:
    for payload in reversed(extract_json_objects(logs)):
        report = payload.get("report") if isinstance(payload, dict) else None
        if isinstance(report, dict):
            return report
    return None


def extract_json_objects(text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    starts = [index for index, char in enumerate(text) if char == "{"]
    for start in starts:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:index + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(value, dict):
                        objects.append(value)
                    break
    return objects


def validate_firestore(project_id: str, report: dict[str, Any]) -> str:
    try:
        from google.cloud import firestore
    except Exception as exc:
        return f"WARN ({exc})"

    accounts = report.get("accounts") or []
    if not accounts:
        return "WARN (sem contas no report)"

    try:
        db = firestore.Client(project=project_id)
        for account in accounts:
            account_id = account.get("id")
            if not account_id:
                continue
            for subcollection in ("emails", "classifications", "action_plans"):
                docs = list(
                    db.collection("accounts")
                    .document(account_id)
                    .collection(subcollection)
                    .limit(1)
                    .stream()
                )
                if not docs:
                    return f"WARN ({account_id}/{subcollection} sem documentos visiveis)"
    except Exception as exc:
        return f"WARN ({exc})"
    return "OK"


if __name__ == "__main__":
    raise SystemExit(main())
