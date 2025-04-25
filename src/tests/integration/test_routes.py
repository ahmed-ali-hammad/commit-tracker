import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.main import DatabaseManager
from src.db.models import Base
from src.webapp.main import app, get_settings
from src.webapp.settings import Settings

client = TestClient(app)


def get_settings_test():
    return Settings(
        GITHUB_API_URL="https://github-api-test-only.de",
        GITHUB_ACCESS_TOKEN="dummy-token",
        DATABASE_USER="db_user_test",
        DATABASE_PASSWORD="Zds5DuF6TLbZexOZHjP",
        DATABASE_HOST="commit-tracker-db-test",
        DATABASE_PORT="3306",
        DATABASE_NAME="commit_history",
    )


async def get_session_test():
    engine = create_async_engine(get_settings_test().ASYNC_DATABASE_URI)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="class", autouse=True)
async def override_dependency():
    app.dependency_overrides[DatabaseManager.get_session] = get_session_test
    app.dependency_overrides[get_settings] = get_settings_test
    yield
    app.dependency_overrides = {}


class TestRoutes:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
