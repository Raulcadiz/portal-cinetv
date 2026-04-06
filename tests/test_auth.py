"""
Tests for admin authentication — POST /api/admin/login
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seed_admin):
    """Valid credentials return a JWT access token."""
    response = await client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "testpassword"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, seed_admin):
    """Wrong password returns 401."""
    response = await client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient, seed_admin):
    """Unknown username returns 401."""
    response = await client.post(
        "/api/admin/login",
        json={"username": "nobody", "password": "testpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_requires_token(client: AsyncClient, seed_admin):
    """Accessing a protected endpoint without token returns 403 or 401."""
    response = await client.get(
        "/api/portal/playlists", params={"mac": "AA:BB:CC:DD:EE:FF"}
    )
    assert response.status_code in (401, 403)
