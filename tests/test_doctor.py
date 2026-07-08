from __future__ import annotations

import subprocess

from scripts import doctor


def completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def test_check_summary_counts_statuses():
    summary = doctor.CheckSummary()

    summary.add("OK")
    summary.add("WARN")
    summary.add("ERROR")

    assert summary.ok == 1
    assert summary.warn == 1
    assert summary.error == 1


def test_check_command_success_and_failure(monkeypatch, capsys):
    summary = doctor.CheckSummary()
    monkeypatch.setattr(doctor, "run", lambda command: completed(command, stdout="pip 1.0\n"))

    doctor.check_command(summary, "pip", ["python", "-m", "pip"])

    assert summary.ok == 1
    assert "[OK] pip: pip 1.0" in capsys.readouterr().out

    monkeypatch.setattr(doctor, "run", lambda command: completed(command, returncode=1, stderr="boom\n"))
    doctor.check_command(summary, "pip", ["python", "-m", "pip"])

    assert summary.error == 1
    assert "[ERROR] pip: boom" in capsys.readouterr().out


def test_check_command_exception_is_error(monkeypatch, capsys):
    summary = doctor.CheckSummary()

    def raise_timeout(command):
        raise TimeoutError("slow")

    monkeypatch.setattr(doctor, "run", raise_timeout)

    doctor.check_command(summary, "gcloud", ["gcloud"])

    assert summary.error == 1
    assert "[ERROR] gcloud: slow" in capsys.readouterr().out


def test_check_venv_warns_when_not_active(monkeypatch):
    summary = doctor.CheckSummary()
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    doctor.check_venv(summary)

    assert summary.warn == 1


def test_check_executable_missing_is_error(monkeypatch):
    summary = doctor.CheckSummary()
    monkeypatch.setattr(doctor.shutil, "which", lambda executable: None)

    doctor.check_executable(summary, "Docker instalado", "docker", ["docker", "--version"])

    assert summary.error == 1


def test_check_gcloud_auth_success_and_failure(monkeypatch):
    summary = doctor.CheckSummary()
    monkeypatch.setattr(doctor.shutil, "which", lambda executable: "/bin/gcloud")
    monkeypatch.setattr(doctor, "run", lambda command: completed(command, stdout="user@example.com\n"))

    doctor.check_gcloud_auth(summary)

    assert summary.ok == 1

    monkeypatch.setattr(doctor, "run", lambda command: completed(command, returncode=1, stderr="no auth"))
    doctor.check_gcloud_auth(summary)

    assert summary.error == 1


def test_check_expected_value_detects_mismatch():
    summary = doctor.CheckSummary()

    doctor.check_expected_value(summary, "Projeto esperado", "wrong", doctor.EXPECTED_PROJECT_ID)

    assert summary.error == 1


def test_check_gcloud_region_warns_when_unset(monkeypatch):
    summary = doctor.CheckSummary()
    monkeypatch.setattr(doctor, "run", lambda command: completed(command, stdout="(unset)\n"))

    doctor.check_gcloud_region(summary, doctor.EXPECTED_REGION)

    assert summary.warn == 1


def test_check_gcloud_region_errors_on_wrong_region(monkeypatch):
    summary = doctor.CheckSummary()

    def fake_run(command):
        if command[3] == "run/region":
            return completed(command, stdout="us-central1\n")
        return completed(command, stdout="southamerica-east1\n")

    monkeypatch.setattr(doctor, "run", fake_run)

    doctor.check_gcloud_region(summary, doctor.EXPECTED_REGION)

    assert summary.error == 1


def test_check_api_secret_and_job_failures(monkeypatch):
    summary = doctor.CheckSummary()
    monkeypatch.setattr(doctor, "run", lambda command: completed(command, returncode=1, stderr="not found"))

    doctor.check_api(summary, doctor.EXPECTED_PROJECT_ID, "gmail.googleapis.com")
    doctor.check_secret(summary, doctor.EXPECTED_PROJECT_ID, "missing-secret")
    doctor.check_job(summary, doctor.EXPECTED_PROJECT_ID, doctor.EXPECTED_REGION, "missing-job")

    assert summary.error == 3


def test_main_success(monkeypatch, capsys):
    def fake_run(command, timeout=30):
        joined = " ".join(command)
        if "config get-value core/project" in joined:
            return completed(command, stdout=f"{doctor.EXPECTED_PROJECT_ID}\n")
        if "config get-value run/region" in joined:
            return completed(command, stdout=f"{doctor.EXPECTED_REGION}\n")
        if "config get-value compute/region" in joined:
            return completed(command, stdout="(unset)\n")
        if "auth list" in joined:
            return completed(command, stdout="user@example.com\n")
        if "services list" in joined:
            return completed(command, stdout=f"{command[6].removeprefix('--filter=config.name:')}\n")
        if "secrets describe" in joined:
            return completed(command, stdout="secret\n")
        if "jobs describe" in joined:
            return completed(command, stdout="assistente-pessoal-diario\n")
        return completed(command, stdout="ok\n")

    monkeypatch.setenv("VIRTUAL_ENV", ".venv")
    monkeypatch.setattr(doctor.shutil, "which", lambda executable: f"/bin/{executable}")
    monkeypatch.setattr(doctor, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["doctor.py"])

    assert doctor.main() == 0
    assert "[ERROR] 0 checks" in capsys.readouterr().out


def test_main_fails_when_api_secret_and_job_missing(monkeypatch):
    def fake_run(command, timeout=30):
        joined = " ".join(command)
        if "config get-value core/project" in joined:
            return completed(command, stdout=f"{doctor.EXPECTED_PROJECT_ID}\n")
        if "config get-value run/region" in joined:
            return completed(command, stdout=f"{doctor.EXPECTED_REGION}\n")
        if "config get-value compute/region" in joined:
            return completed(command, stdout="(unset)\n")
        if "auth list" in joined:
            return completed(command, stdout="user@example.com\n")
        if "services list" in joined or "secrets describe" in joined or "jobs describe" in joined:
            return completed(command, returncode=1, stderr="missing\n")
        return completed(command, stdout="ok\n")

    monkeypatch.setenv("VIRTUAL_ENV", ".venv")
    monkeypatch.setattr(doctor.shutil, "which", lambda executable: f"/bin/{executable}")
    monkeypatch.setattr(doctor, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["doctor.py"])

    assert doctor.main() == 1
