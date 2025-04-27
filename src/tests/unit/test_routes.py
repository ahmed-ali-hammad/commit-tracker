from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import DatabaseManager
from src.webapp.main import app, get_settings
from src.webapp.settings import Settings

client = TestClient(app)


async def get_mock_session_test():
    mock_session = MagicMock(spec=AsyncSession)
    yield mock_session


def get_settings_test():
    return Settings(
        GITHUB_API_URL="https://github-api-test-only.de",
        GITHUB_ACCESS_TOKEN="dummy-token",
        DATABASE_USER="db_hero",
        DATABASE_PASSWORD="supersecret123",
        DATABASE_HOST="database-central.de",
        DATABASE_PORT="3306",
        DATABASE_NAME="testdb",
    )


@pytest_asyncio.fixture(scope="class", autouse=True)
async def override_dependency():
    app.dependency_overrides[DatabaseManager.get_session] = get_mock_session_test
    app.dependency_overrides[get_settings] = get_settings_test
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
class TestRoutes:

    async def test_health_check_healthy(self, mocker):
        mock_check_db_connection = mocker.patch(
            "src.webapp.main.check_db_connection",
            return_value=True,
        )
        response = client.get("/health")

        mock_check_db_connection.assert_called_once()
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

    async def test_health_check_not_healthy(self, mocker):
        mock_check_db_connection = mocker.patch(
            "src.webapp.main.check_db_connection",
            return_value=False,
        )
        response = client.get("/health")

        mock_check_db_connection.assert_called_once()
        assert response.status_code == 500
        assert response.json() == {"detail": "Database connection failed"}
