from __future__ import annotations

from app.core.classifier import classify_email
from app.core.models import Category, EmailItem, Priority


def make_email(subject: str, sender: str = "sender@example.com", snippet: str = "") -> EmailItem:
    return EmailItem(
        account_id="acc",
        account_email="acc@example.com",
        provider="gmail",
        id="msg-1",
        thread_id="thread-1",
        subject=subject,
        sender=sender,
        recipients=["acc@example.com"],
        snippet=snippet,
    )


def test_classifier_marks_security_as_critical_without_mutation():
    result = classify_email(make_email("Novo login detectado"))

    assert result.category == Category.SECURITY
    assert result.priority == Priority.CRITICA
    assert result.should_mark_read is False


def test_classifier_detects_newsletter_as_noise_without_mark_read():
    result = classify_email(make_email("Newsletter semanal", snippet="clique para descadastrar"))

    assert result.category == Category.NEWSLETTER
    assert result.priority == Priority.RUIDO
    assert result.should_mark_read is False


def test_classifier_detects_event_hint():
    result = classify_email(make_email("Reuniao amanha 14:30"))

    assert result.category == Category.EVENTO
    assert result.priority == Priority.IMPORTANTE
    assert result.possible_event is True
