from __future__ import annotations

import subprocess

from scripts import smoke
from scripts.smoke import (
    FirestoreStatus,
    find_known_error,
    find_report,
    strip_log_prefix,
    strip_log_prefixes,
    validate_report,
)


def test_strip_log_prefix_removes_timestamp_and_stream_prefix():
    line = '2026-07-08T14:30:01.123456Z stdout F   "finished_at": "2026-07-08T14:30:01Z",'

    assert strip_log_prefix(line) == '"finished_at": "2026-07-08T14:30:01Z",'


def test_find_report_from_prefixed_fragmented_cloud_logs():
    logs = """
2026-07-08T14:30:00.000000Z stdout F 2026-07-08 14:30:00 INFO Gmail retornou 10 mensagens para conta pessoal_google
2026-07-08T14:30:01.000000Z stderr F Regional Access Boundary HTTP request failed...
2026-07-08T14:30:01.000001Z stderr F Gaia id not found...
2026-07-08T14:30:02.000000Z stdout F {
2026-07-08T14:30:02.000001Z stdout F   "finished_at": "2026-07-08T14:30:02Z",
2026-07-08T14:30:02.000002Z stdout F   "dry_run": true,
2026-07-08T14:30:02.000003Z stdout F   "report": {
2026-07-08T14:30:02.000004Z stdout F     "total": 10,
2026-07-08T14:30:02.000005Z stdout F     "errors": [],
2026-07-08T14:30:02.000006Z stdout F     "total_by_category": {
2026-07-08T14:30:02.000007Z stdout F       "financeiro": 1,
2026-07-08T14:30:02.000008Z stdout F       "outros": 9
2026-07-08T14:30:02.000009Z stdout F     },
2026-07-08T14:30:02.000010Z stdout F     "total_by_priority": {
2026-07-08T14:30:02.000011Z stdout F       "normal": 9,
2026-07-08T14:30:02.000012Z stdout F       "alta": 1
2026-07-08T14:30:02.000013Z stdout F     },
2026-07-08T14:30:02.000014Z stdout F     "planned_actions": [
2026-07-08T14:30:02.000015Z stdout F       {"type": "review_financial", "dry_run": true}
2026-07-08T14:30:02.000016Z stdout F     ]
2026-07-08T14:30:02.000017Z stdout F   }
2026-07-08T14:30:02.000018Z stdout F }
"""

    report = find_report(logs)

    assert report is not None
    assert report["total"] == 10
    assert report["errors"] == []
    assert report["total_by_category"] == {"financeiro": 1, "outros": 9}
    assert report["planned_actions"] == [{"type": "review_financial", "dry_run": True}]


def test_find_report_accepts_empty_planned_actions():
    logs = """
2026-07-08T14:30:02Z stdout F {
2026-07-08T14:30:02Z stdout F   "finished_at": "2026-07-08T14:30:02Z",
2026-07-08T14:30:02Z stdout F   "dry_run": true,
2026-07-08T14:30:02Z stdout F   "report": {
2026-07-08T14:30:02Z stdout F     "total": 10,
2026-07-08T14:30:02Z stdout F     "errors": [],
2026-07-08T14:30:02Z stdout F     "total_by_category": {},
2026-07-08T14:30:02Z stdout F     "total_by_priority": {"normal": 10},
2026-07-08T14:30:02Z stdout F     "planned_actions": []
2026-07-08T14:30:02Z stdout F   }
2026-07-08T14:30:02Z stdout F }
"""

    report = find_report(logs)

    assert report is not None
    assert report["planned_actions"] == []
    assert report["total_by_priority"] == {"normal": 10}


def test_validate_report_warns_when_planned_actions_is_empty():
    status = validate_report(
        {
            "total": 10,
            "errors": [],
            "total_by_category": {"outros": 10},
            "planned_actions": [],
        }
    )

    assert status.error is None
    assert status.emails == 10
    assert status.classifications == 10
    assert status.action_plans == 0
    assert status.warnings == ["Nenhum action plan encontrado no report."]


def test_known_error_in_logs_is_detected_as_failure_signal():
    assert find_known_error("RefreshError: invalid_grant") == "RefreshError"


def test_find_report_keeps_working_with_plain_json():
    logs = '{\n  "finished_at": "now",\n  "dry_run": true,\n  "report": {"total": 1, "errors": []}\n}'

    assert find_report(strip_log_prefixes(logs)) == {"total": 1, "errors": []}


def test_main_uses_firestore_fallback_when_logs_are_truncated(monkeypatch, capsys):
    calls = []

    def fake_run(command):
        calls.append(command)
        if command == ["make", "run-job"]:
            return subprocess.CompletedProcess(command, 0, stdout="Execution [assistente-pessoal-diario-abc]\n", stderr="")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='2026-07-08T14:30:00Z stdout F Gmail retornou 10 mensagens\n{"finished_at":',
            stderr="Regional Access Boundary HTTP request failed...\nGaia id not found...\n",
        )

    monkeypatch.setattr(smoke, "run", fake_run)
    monkeypatch.setattr(
        smoke,
        "validate_firestore",
        lambda project_id, account_id=smoke.DEFAULT_ACCOUNT_ID: FirestoreStatus(
            emails=10,
            classifications=10,
            action_plans=0,
            warnings=["Firestore sem action plans em accounts/pessoal_google/action_plans."],
        ),
    )
    monkeypatch.setattr("sys.argv", ["smoke.py"])

    assert smoke.main() == 0
    output = capsys.readouterr().out
    assert "Report final nao encontrado completo nos logs; validando Firestore." in output
    assert "emails processados: 10" in output
    assert "classificacoes: 10" in output
    assert "action plans: 0" in output


def test_main_fails_on_known_error_in_logs(monkeypatch, capsys):
    def fake_run(command):
        if command == ["make", "run-job"]:
            return subprocess.CompletedProcess(command, 0, stdout="Execution [assistente-pessoal-diario-abc]\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="RefreshError", stderr="")

    monkeypatch.setattr(smoke, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["smoke.py"])

    assert smoke.main() == 1
    assert "Padrao proibido encontrado nos logs: RefreshError" in capsys.readouterr().out
