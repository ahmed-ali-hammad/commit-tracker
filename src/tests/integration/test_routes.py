import pytest
import pytest_asyncio
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from src.db.main import DatabaseManager
from src.tests.integration.helpers import get_session_test, get_settings_test
from src.webapp.main import app, get_settings

client = TestClient(app)


@pytest_asyncio.fixture(scope="class", autouse=True)
async def override_dependency():
    app.dependency_overrides[DatabaseManager.get_session] = get_session_test
    app.dependency_overrides[get_settings] = get_settings_test
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
class TestRoutes:

    async def test_health_check_healthy(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

    async def test_trigger_commit_fetch_success(self, mocker):
        mocker.patch(
            "src.domain.service.CommitService.retrieve_and_store_commits"
        )  # mock here to avoid calling git provider with each run

        response = client.post("/commits/trigger-fetch")

        assert response.status_code == 200
        assert response.json() == {"status": "Processing started in background"}

    async def test_trigger_commit_fetch_failure(self, mocker):
        mocker.patch.object(
            BackgroundTasks, "add_task", side_effect=Exception("Test error")
        )

        response = client.post("/commits/trigger-fetch")

        assert response.status_code == 500
        assert response.json() == {"detail": "Something went wrong"}

    async def test_get_commits_by_author_name_success(self, create_dummpy_commits):
        author_identifier = "Sean Nguyen"
        response = client.get(f"/commits/by-author/{author_identifier}")
        assert response.status_code == 200
        assert any(commit["author_name"] == "Sean Nguyen" for commit in response.json())

    async def test_get_commits_by_author_email_success(self, create_dummpy_commits):
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

    async def test_get_commits_by_author_case_insensitive_name(
        self, create_dummpy_commits
    ):
        author_identifier = "sean nguyen"
        response = client.get(f"/commits/by-author/{author_identifier}")

        assert response.status_code == 200
        data = response.json()

        assert any(
            commit["author_name"].lower() == author_identifier.lower()
            for commit in data
        )

    async def test_get_commits_by_author_case_insensitive_email(
        self, create_dummpy_commits
    ):
        author_identifier = "JAKE@NETOPS.DEV"
        response = client.get(f"/commits/by-author/{author_identifier}")

        assert response.status_code == 200
        data = response.json()

        assert any(
            commit["author_email"].lower() == author_identifier.lower()
            for commit in data
        )

    async def test_get_commits_by_author_not_found(self):
        author_identifier = "Non Existent"
        response = client.get(f"/commits/by-author/{author_identifier}")
        assert response.status_code == 404
        assert response.json()["detail"] == "No commits found for: Non Existent"

    async def test_get_aggregated_commits_data_by_author(self, create_dummpy_commits):
        response = client.get("/commits/authors/summary")
        summary = response.json()

        assert response.status_code == 200
        assert any(author["author_name"] == "Sean Nguyen" for author in summary)
        assert any("total_number_of_commits" in author for author in summary)
        assert all("latest_commit_date" in author for author in summary)

    async def test_recent_commits_grouped_by_author_success(
        self, create_dummpy_commits
    ):
        response = client.get("/commits/authors/recent")
        assert response.status_code == 200

        data = response.json()
        expected_keys = ["author_name", "commits"]

        assert isinstance(data, list)
        for key in expected_keys:
            assert key in data[0]
