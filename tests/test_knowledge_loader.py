"""Tests for Phase 4 knowledge-base loading."""

from backend.app.knowledge.loader import load_knowledge_documents


def test_curated_knowledge_base_contains_expected_documents() -> None:
    documents = load_knowledge_documents()

    assert len(documents) == 5
    assert {document.metadata["category"] for document in documents} == {
        "faq",
        "refund_policy",
        "cancellation_policy",
        "shipping_policy",
        "payment_policy",
    }
    assert all(document.content.startswith("# ") for document in documents)
