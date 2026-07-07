from __future__ import annotations

from app.storage.firestore_store import FirestoreStore


def test_processed_email_id_is_stable_and_path_safe():
    store = object.__new__(FirestoreStore)

    doc_id = store._processed_email_id("pessoal", "gmail", "abc/123")

    assert doc_id == "pessoal_gmail_abc_123"
