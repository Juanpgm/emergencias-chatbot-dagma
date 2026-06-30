from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from admin.app.core.auth import create_access_token
from shared.core.database import get_db


def _make_db_mock():
    session = AsyncMock()
    session.add = MagicMock()  # synchronous in SQLAlchemy

    execute_result = MagicMock()
    scalar_result = MagicMock()
    scalar_result.all.return_value = []
    execute_result.scalars.return_value = scalar_result
    execute_result.scalar_one_or_none = MagicMock(return_value=None)
    execute_result.scalar_one = MagicMock(return_value=None)

    session.execute.return_value = execute_result
    return session


async def _override_get_db():
    yield _make_db_mock()


@pytest.fixture
def app():
    from admin.app.main import app as admin_app
    return admin_app


@pytest.fixture
async def client(app):
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    return create_access_token("user:admin")


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
