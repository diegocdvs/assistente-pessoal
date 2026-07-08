from __future__ import annotations

from app.core.models import ActionPlan, Category, Classification, EmailEntity, Priority
from app.storage.persistence import FirestorePersistence, _safe_document_id


class FakeSnapshot:
    def __init__(self, exists: bool) -> None:
        self.exists = exists


class FakeDocument:
    def __init__(self, exists: bool = False) -> None:
        self.exists = exists
        self.payloads = []
        self.children = {}

    def collection(self, name: str):
        self.children.setdefault(name, FakeCollection(self.exists))
        return self.children[name]

    def document(self, name: str):
        self.children.setdefault(name, FakeDocument(self.exists))
        return self.children[name]

    def get(self):
        return FakeSnapshot(self.exists)

    def set(self, payload, merge=False):
        self.payloads.append({"payload": payload, "merge": merge})
        self.exists = True


class FakeCollection:
    def __init__(self, exists: bool = False) -> None:
        self.exists = exists
        self.documents = {}

    def document(self, name: str | None = None):
        key = name or "generated-run"
        self.documents.setdefault(key, FakeDocument(self.exists))
        return self.documents[key]


class FakeClient:
    def __init__(self, email_exists: bool = False) -> None:
        self.email_exists = email_exists
        self.collections = {}

    def collection(self, name: str):
        self.collections.setdefault(name, FakeCollection(self.email_exists))
        return self.collections[name]


def make_email() -> EmailEntity:
    return EmailEntity(
        id="abc/123",
        provider="gmail",
        account_id="acc",
        account_email="acc@example.com",
        thread_id="thread",
        subject="Fatura",
        sender="sender@example.com",
        recipients=["acc@example.com"],
        snippet="Pagamento",
    )


def test_safe_document_id_replaces_slashes():
    assert _safe_document_id("abc/123") == "abc_123"


def test_upsert_email_creates_first_seen_for_new_email():
    persistence = object.__new__(FirestorePersistence)
    persistence.client = FakeClient(email_exists=False)
    classification = Classification(Category.FINANCEIRO, Priority.ALTA, "Financeiro.", 0.8)
    actions = [ActionPlan("review_financial", "Mensagem financeira.", True)]

    result = persistence.upsert_email(make_email(), classification, actions)

    doc = persistence._email_document(make_email())
    payload = doc.payloads[-1]["payload"]
    assert result.existed is False
    assert "first_seen_at" in payload
    assert payload["classification"]["category"] == "financeiro"
    assert payload["actions"][0]["type"] == "review_financial"


def test_upsert_email_updates_last_seen_for_existing_email_without_first_seen():
    persistence = object.__new__(FirestorePersistence)
    persistence.client = FakeClient(email_exists=True)
    classification = Classification(Category.FINANCEIRO, Priority.ALTA, "Financeiro.", 0.8)

    result = persistence.upsert_email(make_email(), classification, [])

    doc = persistence._email_document(make_email())
    payload = doc.payloads[-1]["payload"]
    assert result.existed is True
    assert "last_seen_at" in payload
    assert "first_seen_at" not in payload
