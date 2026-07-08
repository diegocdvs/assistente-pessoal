from __future__ import annotations

from app.core.classifier import classify_email
from app.core.models import Category, EmailEntity, Priority


def make_email(subject: str, sender: str = "sender@example.com", snippet: str = "") -> EmailEntity:
    return EmailEntity(
        id="msg-1",
        provider="gmail",
        account_id="acc",
        account_email="acc@example.com",
        thread_id="thread-1",
        subject=subject,
        sender=sender,
        recipients=["acc@example.com"],
        snippet=snippet,
    )


def test_classifier_marks_security_as_critical_with_confidence():
    result = classify_email(make_email("Novo login detectado"))

    assert result.category == Category.SEGURANCA
    assert result.priority == Priority.CRITICA
    assert result.confidence >= 0.9


def test_promotion_with_time_or_percent_does_not_become_event():
    result = classify_email(make_email("Oferta 24h com 50% desconto ate 14:30"))

    assert result.category == Category.PROMOCAO
    assert result.priority == Priority.RUIDO
    assert result.possible_event is False


def test_tutorial_newsletter_does_not_become_event():
    result = classify_email(make_email("Tutorial semanal: configure sua agenda amanha"))

    assert result.category == Category.NEWSLETTER
    assert result.priority == Priority.RUIDO
    assert result.possible_event is False


def test_job_offer_is_work_with_normal_priority_by_default():
    result = classify_email(make_email("Nova vaga para desenvolvedor"))

    assert result.category == Category.TRABALHO
    assert result.priority == Priority.NORMAL


def test_job_offer_with_interview_is_high_priority_work():
    result = classify_email(make_email("Convite para entrevista da vaga"))

    assert result.category == Category.TRABALHO
    assert result.priority == Priority.ALTA


def test_receipt_goes_to_purchase_or_finance_not_event():
    result = classify_email(make_email("Recibo da compra realizada hoje as 12:00"))

    assert result.category in {Category.COMPRA, Category.FINANCEIRO}
    assert result.category != Category.EVENTO


def test_classifier_detects_event_hint():
    result = classify_email(make_email("Reuniao amanha 14:30"))

    assert result.category == Category.EVENTO
    assert result.priority == Priority.ALTA
    assert result.possible_event is True
