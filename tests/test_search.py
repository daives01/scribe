"""Tests for search endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_search_requires_auth(client: TestClient):
    """Test that search requires authentication."""
    response = client.post(
        "/search",
        json={"query": "test"},
    )
    assert response.status_code == 401


def test_ask_requires_auth(client: TestClient):
    """Test that ask requires authentication."""
    response = client.post(
        "/ask",
        json={"question": "What are my todos?"},
    )
    assert response.status_code == 401


# Note: Full search tests require Ollama to be running
# These are placeholder tests for the API structure

@pytest.mark.skip(reason="Requires Ollama connection")
def test_search_notes(client: TestClient, auth_headers, test_note):
    """Test semantic search."""
    response = client.post(
        "/search",
        headers=auth_headers,
        json={"query": "Python programming", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


@pytest.mark.skip(reason="Requires Ollama connection")
def test_ask_question(client: TestClient, auth_headers, test_note):
    """Test RAG question answering."""
    response = client.post(
        "/ask",
        headers=auth_headers,
        json={"question": "What is my note about?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
