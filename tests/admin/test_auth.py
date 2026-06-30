from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.models.emergencia import AdminUser


@pytest.mark.asyncio
async def test_login_success(client):
    response = await client.post("/auth/login", json={"username": "admin", "password": "change-me-in-production"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    response = await client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_missing_fields(client):
    response = await client.post("/auth/login", json={"username": "admin"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_bcrypt_verify_existing_user(app, client):
    """Login against an existing AdminUser with hashed password uses bcrypt, not plaintext."""
    existing_user = AdminUser(username="admin", display_name="Admin")
    existing_user.set_password("change-me-in-production")

    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=existing_user)

    from shared.core.database import get_db
    from unittest.mock import AsyncMock

    async def _override_with_user():
        session = AsyncMock()
        session.add = MagicMock()
        session.execute.return_value = execute_result
        yield session

    app.dependency_overrides[get_db] = _override_with_user

    response = await client.post("/auth/login", json={"username": "admin", "password": "change-me-in-production"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_bcrypt_wrong_password_existing_user(app):
    """Wrong password against an existing hashed user returns 401."""
    existing_user = AdminUser(username="admin", display_name="Admin")
    existing_user.set_password("correct-password")

    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=existing_user)

    from httpx import ASGITransport, AsyncClient
    from shared.core.database import get_db
    from unittest.mock import AsyncMock

    async def _override_with_user():
        session = AsyncMock()
        session.add = MagicMock()
        session.execute.return_value = execute_result
        yield session

    app.dependency_overrides[get_db] = _override_with_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/auth/login", json={"username": "admin", "password": "wrong-password"})

    assert response.status_code == 401
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_refresh_token_type_is_refresh(client):
    """Token returned in refresh_token field must be type=refresh, not access."""
    from jose import jwt
    from admin.app.core.auth import _get_secret

    login_resp = await client.post("/auth/login", json={"username": "admin", "password": "change-me-in-production"})
    data = login_resp.json()

    refresh_payload = jwt.decode(data["refresh_token"], _get_secret(), algorithms=["HS256"])
    access_payload = jwt.decode(data["access_token"], _get_secret(), algorithms=["HS256"])

    assert refresh_payload.get("type") == "refresh"
    assert access_payload.get("type") == "access"


@pytest.mark.asyncio
async def test_access_token_rejected_as_refresh(client):
    """Using an access token as a refresh token must return 401."""
    login_resp = await client.post("/auth/login", json={"username": "admin", "password": "change-me-in-production"})
    access_token = login_resp.json()["access_token"]

    response = await client.post("/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client):
    login_resp = await client.post("/auth/login", json={"username": "admin", "password": "change-me-in-production"})
    data = login_resp.json()
    refresh_token = data["refresh_token"]

    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    new_data = response.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    response = await client.post("/auth/refresh", json={"refresh_token": "invalid_token"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "admin"
