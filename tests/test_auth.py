"""Tests for authentication endpoints."""

from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    """Test user registration."""
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "password": "securepassword",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_username(client: TestClient, test_user):
    """Test that duplicate usernames are rejected."""
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",  # Same as test_user
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


def test_login_success(client: TestClient, test_user):
    """Test successful login."""
    response = client.post(
        "/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, test_user):
    """Test login with wrong password."""
    response = client.post(
        "/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user(client: TestClient):
    """Test login with non-existent user."""
    response = client.post(
        "/auth/login",
        data={
            "username": "nonexistent",
            "password": "password",
        },
    )
    assert response.status_code == 401


def test_get_current_user(client: TestClient, auth_headers, test_user):
    """Test getting current user info."""
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert "email" not in data


def test_get_current_user_no_auth(client: TestClient):
    """Test getting current user without authentication."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_generate_api_token(client: TestClient, auth_headers):
    """Test generating a long-lived API token."""
    response = client.post("/auth/api-token", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "api_token" in data
    assert len(data["api_token"]) > 30

    # Test using the token
    api_token = data["api_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {api_token}"})
    assert response.status_code == 200


def test_revoke_api_token(client: TestClient, auth_headers):
    """Test revoking an API token."""
    # Generate token first
    response = client.post("/auth/api-token", headers=auth_headers)
    api_token = response.json()["api_token"]

    # Verify it works
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {api_token}"})
    assert response.status_code == 200

    # Revoke it
    response = client.delete("/auth/api-token", headers=auth_headers)
    assert response.status_code == 204

    # Verify it acts like it's revoked
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {api_token}"})
    # NOTE: The current implementation of ApiToken logic checks DB for api_token match.
    # If revoked (set to None), it won't match "None" against the token string.
    assert response.status_code == 401
