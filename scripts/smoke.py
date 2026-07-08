from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any


DEFAULT_ACCOUNT_ID = "pessoal_google"
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
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID)
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
        print("[WARN] Falha ao ler logs da execucao; usando fallback Firestore.")
        logs = ""

    known_error = find_known_error(logs)
    if known_error:
        print(f"[ERROR] Padrao proibido encontrado nos logs: {known_error}")
        return 1

    print_log_signals(logs)

    report = find_report(logs)
    firestore_status: FirestoreStatus | None = None

    if report is None:
        print("[WARN] Report final nao encontrado completo nos logs; validando Firestore.")
        firestore_status = validate_firestore(args.project_id, args.account_id)
        if firestore_status.error:
            print(f"[ERROR] {firestore_status.error}")
            return 1
        for warning in firestore_status.warnings:
            print(f"[WARN] {warning}")
        emails_processed = firestore_status.emails
        classifications = firestore_status.classifications
        action_plans = firestore_status.action_plans
        duration = "desconhecida"
    else:
        report_status = validate_report(report)
        if report_status.error:
            print(f"[ERROR] {report_status.error}")
            return 1
        for warning in report_status.warnings:
            print(f"[WARN] {warning}")
        emails_processed = report_status.emails
        classifications = report_status.classifications
        action_plans = report_status.action_plans
        duration = report.get("duration_seconds", "desconhecida")

    print("\n== Resumo smoke ==")
    print(f"execucao: {execution}")
    print(f"duracao: {duration}")
    print(f"emails processados: {emails_processed}")
    print(f"classificacoes: {classifications}")
    print(f"action plans: {action_plans}")
    print(f"firestore: {firestore_status.summary if firestore_status else 'nao usado'}")
    print("status: OK")
    return 0


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True)


class SmokeStatus:
    def __init__(
        self,
        *,
        emails: int = 0,
        classifications: int = 0,
        action_plans: int = 0,
        error: str | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        self.emails = emails
        self.classifications = classifications
        self.action_plans = action_plans
        self.error = error
        self.warnings = warnings or []


class FirestoreStatus(SmokeStatus):
    @property
    def summary(self) -> str:
        return (
            f"emails={self.emails}, "
            f"classifications={self.classifications}, "
            f"action_plans={self.action_plans}"
        )


def find_known_error(logs: str) -> str | None:
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in logs:
            return pattern
    return None


def print_log_signals(logs: str) -> None:
    if "Gmail retornou" in logs:
        print("[OK] Sinal nos logs: Gmail retornou mensagens.")
    else:
        print("[WARN] Sinal ausente nos logs: Gmail retornou.")

    if 'errors": []' in logs or '"errors": []' in strip_log_prefixes(logs):
        print("[OK] Sinal nos logs: errors vazio.")
    else:
        print("[WARN] Sinal ausente nos logs: errors vazio.")


def validate_report(report: dict[str, Any]) -> SmokeStatus:
    errors = report.get("errors")
    if errors != []:
        return SmokeStatus(error=f"Report possui erros: {errors}")

    emails_processed = int(report.get("total") or 0)
    total_by_category = report.get("total_by_category") or {}
    total_by_priority = report.get("total_by_priority") or {}
    classifications = sum(int(value) for value in total_by_category.values()) or sum(
        int(value) for value in total_by_priority.values()
    )
    action_plans = len(report.get("planned_actions") or [])

    if emails_processed <= 0:
        return SmokeStatus(error="Nenhum email processado.")
    if not total_by_category and not total_by_priority:
        return SmokeStatus(error="Nenhum total de classificacao ou prioridade encontrado no report.")

    warnings = []
    if action_plans <= 0:
        warnings.append("Nenhum action plan encontrado no report.")

    return SmokeStatus(
        emails=emails_processed,
        classifications=classifications,
        action_plans=action_plans,
        warnings=warnings,
    )


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
    for payload in reversed(extract_json_objects(strip_log_prefixes(logs))):
        report = payload.get("report") if isinstance(payload, dict) else None
        if (
            isinstance(report, dict)
            and "finished_at" in payload
            and "dry_run" in payload
        ):
            return report
    return None


def strip_log_prefixes(logs: str) -> str:
    return "\n".join(strip_log_prefix(line) for line in logs.splitlines())


def strip_log_prefix(line: str) -> str:
    stripped = line.lstrip()
    if _looks_like_json_line(stripped):
        return stripped

    match = re.match(
        r"^\d{4}-\d{2}-\d{2}(?:T|\s+)\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s+(.*)$",
        stripped,
    )
    if match:
        stripped = match.group(1).lstrip()

    match = re.match(r"^(?:stdout|stderr)\s+[A-Z]\s+(.*)$", stripped)
    if match:
        stripped = match.group(1).lstrip()

    if _looks_like_json_line(stripped):
        return stripped

    json_fragment = re.search(r'([{}\[\],]|"(?:finished_at|dry_run|report)"\s*:)', stripped)
    if json_fragment:
        return stripped[json_fragment.start():].lstrip()

    return stripped


def _looks_like_json_line(value: str) -> bool:
    return bool(re.match(r'^(?:[{}\[\],]|"[^"]+"\s*:)', value))


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


def validate_firestore(project_id: str, account_id: str = DEFAULT_ACCOUNT_ID) -> FirestoreStatus:
    try:
        from google.cloud import firestore
    except Exception as exc:
        return FirestoreStatus(error=f"Firestore indisponivel para fallback: {exc}")

    try:
        db = firestore.Client(project=project_id)
        counts = {
            subcollection: count_documents(db, account_id, subcollection)
            for subcollection in ("emails", "classifications", "action_plans")
        }
    except Exception as exc:
        return FirestoreStatus(error=f"Falha ao validar Firestore: {exc}")

    if counts["emails"] <= 0:
        return FirestoreStatus(error=f"Firestore sem documentos em accounts/{account_id}/emails.")
    if counts["classifications"] <= 0:
        return FirestoreStatus(error=f"Firestore sem documentos em accounts/{account_id}/classifications.")

    warnings = []
    if counts["action_plans"] <= 0:
        warnings.append(f"Firestore sem action plans em accounts/{account_id}/action_plans.")

    return FirestoreStatus(
        emails=counts["emails"],
        classifications=counts["classifications"],
        action_plans=counts["action_plans"],
        warnings=warnings,
    )


def count_documents(db: Any, account_id: str, subcollection: str) -> int:
    docs = list(
        db.collection("accounts")
        .document(account_id)
        .collection(subcollection)
        .limit(1)
        .stream()
    )
    return len(docs)


if __name__ == "__main__":
    raise SystemExit(main())
