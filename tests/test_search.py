"""Tests for search endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_search_requires_auth(client: TestClient):
    """Test that search requires authentication."""
    response = client.post(
        "/api/search",
        json={"query": "test"},
    )
    assert response.status_code == 401


# Note: Full search tests require Ollama to be running
# These are placeholder tests for API structure


@pytest.mark.skip(reason="Requires Ollama connection")
def test_search_notes(client: TestClient, auth_headers, test_note):
    """Test semantic search."""
    response = client.post(
        "/api/search",
        headers=auth_headers,
        json={"query": "Python programming", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data

    if data["results"]:
        result = data["results"][0]
        assert "note" in result
        assert "similarity" in result
        assert 0 <= result["similarity"] <= 1
