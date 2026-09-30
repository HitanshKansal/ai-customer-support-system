"""Tests for Phase 6 pgvector query construction."""

import pytest
from sqlalchemy.dialects import postgresql

from backend.app.knowledge.search import build_similarity_query, validate_vector


def test_vector_validation_uses_configured_dimension() -> None:
    vector = validate_vector([1.0] * 384)

    assert len(vector) == 384
    assert all(isinstance(value, float) for value in vector)


def test_similarity_query_uses_cosine_distance_and_top_k() -> None:
    query = build_similarity_query([0.0] * 384, top_k=3)
    compiled = str(
        query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False})
    )

    assert "<=>" in compiled
    assert "LIMIT" in compiled
    assert "embedding IS NOT NULL" in compiled


def test_vector_validation_rejects_wrong_dimension() -> None:
    with pytest.raises(ValueError, match="384 dimensions"):
        validate_vector([1.0, 2.0])
