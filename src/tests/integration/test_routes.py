import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.main import DatabaseManager
from src.db.models import Base
from src.tests.integration.conftest import get_settings_test
from src.webapp.main import app, get_settings

client = TestClient(app)


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

    @pytest.mark.asyncio
    async def test_get_commits_by_author_name_success(self):
        author_identifier = "Sean Nguyen"
        response = client.get(f"/commits/by-author/{author_identifier}")
        assert response.status_code == 200
        assert any(commit["author_name"] == "Sean Nguyen" for commit in response.json())

    @pytest.mark.asyncio
    async def test_get_commits_by_author_email_success(self):
        author_identifier = "diego@lsoft.dev"
        response = client.get(f"/commits/by-author/{author_identifier}")

        assert response.status_code == 200
        data = response.json()

        assert any(commit["author_email"] == author_identifier for commit in data)
        assert all("commit_hash" in commit for commit in data)
        for commit in data:
            assert "commit_hash" in commit
            assert "author_name" in commit
            assert "repo_name" in commit
            assert "author_email" in commit

    @pytest.mark.asyncio
    async def test_get_commits_by_author_not_found(self):
        author_identifier = "Non Existent"
        response = client.get(f"/commits/by-author/{author_identifier}")
        assert response.status_code == 404
        assert (
            response.json()["detail"] == "No commits found for the author: Non Existent"
        )

    @pytest.mark.asyncio
    async def test_get_commits_by_author_case_insensitive(self):
        author_identifier = "sean nguyen"
        response = client.get(f"/commits/by-author/{author_identifier}")

        assert response.status_code == 200
        data = response.json()

        assert any(
            commit["author_name"].lower() == author_identifier.lower()
            for commit in data
        )

    @pytest.mark.asyncio
    async def test_get_aggregated_commits_data_by_author(self):
        response = client.get(f"/commits/authors/summary")
        summary = response.json()

        assert response.status_code == 200
        assert any(author["name"] == "Sean Nguyen" for author in summary["authors"])
        assert any("total_commits" in author for author in summary["authors"])
        assert all("latest_commit" in author for author in summary["authors"])

    @pytest.mark.asyncio
    async def test_recent_commits_grouped_by_author_success(self):
        response = client.get("/commits/authors/recent")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
