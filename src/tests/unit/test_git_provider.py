import httpx
import pytest

from src.providers.exceptions import GitProviderDataValidationError


@pytest.mark.asyncio
class TestGitHubProvider:
    async def test_fetch_commit_batch(self, mocker, get_github_provider):
        mock_response = mocker.Mock()
        mock_response.raise_for_status = mocker.Mock()
        mock_response.json.return_value = [{"sha": "123"}]

        mock_httpx_client = mocker.AsyncMock()
        mock_httpx_client.get.return_value = mock_response

        result = await get_github_provider._fetch_commit_batch(
            httpx_client=mock_httpx_client,
            token="toke",
            repo_name="repo",
            batch_number=1,
        )

        mock_httpx_client.get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()
        assert result == [{"sha": "123"}]

    async def test_fetch_commit_batch_unauthorized(self, mocker, get_github_provider):
        mock_response = mocker.Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Unauthorized", request=mocker.Mock(), response=mocker.Mock()
        )

        mock_httpx_client = mocker.AsyncMock()
        mock_httpx_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await get_github_provider._fetch_commit_batch(
                httpx_client=mock_httpx_client,
                token="invalid-token",
                repo_name="repo",
                batch_number=1,
            )

    async def test_parse_and_validate_commit_success(self, get_github_provider):
        commit_data = {
            "sha": "abc123",
            "commit": {
                "author": {
                    "name": "Alice",
                    "email": "alice@lemon.com",
                    "date": 1745703803,
                },
                "message": "Initial commit",
            },
        }
        repo_name = "test-repo"

        result = await get_github_provider._parse_and_validate_commit(
            commit_data, repo_name
        )

        assert result["commit_hash"] == "abc123"
        assert result["author_name"] == "Alice"
        assert result["author_email"] == "alice@lemon.com"
        assert result["commit_message"] == "Initial commit"
        assert result["commit_date"] == 1745703803
        assert result["repo_name"] == "test-repo"

    async def test_parse_and_validate_commit_missing_required_fields(
        self, get_github_provider
    ):
        invalid_commit_data = {
            "commit": {
                "author": {
                    "name": "Bob",
                    "email": "bob@kiwi.com",
                    "date": 1745703203,
                },
                "message": "Fix bug",
            }
        }
        repo_name = "test-repo"

        with pytest.raises(GitProviderDataValidationError) as exc_info:
            await get_github_provider._parse_and_validate_commit(
                invalid_commit_data, repo_name
            )

        assert "Failed to validate commit data for repo: 'test-repo'" in str(
            exc_info.value
        )

    async def test_process_commit_batch_success(
        self, mocker, get_github_provider, sample_raw_commit
    ):
        get_github_provider._parse_and_validate_commit = mocker.AsyncMock(
            return_value={
                "commit_hash": "123abc",
                "author_name": "Alice",
                "author_email": "alice@example.com",
                "commit_message": "Sample commit",
                "commit_date": 1745703803,
                "repo_name": "example/repo",
            }
        )

        commits = [sample_raw_commit]
        success, failed = await get_github_provider._process_commit_batch(
            commits, "example/repo"
        )

        assert len(success) == 1
        assert len(failed) == 0
        assert success[0]["commit_hash"] == "123abc"

    async def test_process_commit_batch_partial_failure(
        self, mocker, get_github_provider, sample_raw_commit
    ):
        invalid_commit = {"sha": "badsha", "commit": {}}

        async def fake_parser(commit_data, repo_name):
            if commit_data["sha"] == "badsha":
                raise GitProviderDataValidationError("Invalid commit")
            return {"commit_hash": "123abc"}

        get_github_provider._parse_and_validate_commit = mocker.AsyncMock(
            side_effect=fake_parser
        )

        commits = [sample_raw_commit, invalid_commit]
        success, failed = await get_github_provider._process_commit_batch(
            commits, "example/repo"
        )

        assert len(success) == 1
        assert len(failed) == 1
        assert failed[0] == "badsha"

    async def test_process_commit_batch_all_fail(self, mocker, get_github_provider):
        bad_commits = [{"sha": f"fail{i}", "commit": {}} for i in range(3)]

        get_github_provider._parse_and_validate_commit = mocker.AsyncMock(
            side_effect=GitProviderDataValidationError("Broken commit")
        )

        success, failed = await get_github_provider._process_commit_batch(
            bad_commits, "example/repo"
        )

        assert len(success) == 0
        assert len(failed) == 3
        assert failed == ["fail0", "fail1", "fail2"]

    async def test_get_and_process_commit_batch_success(
        self, mocker, get_github_provider, mock_httpx_client
    ):

        fake_batch = [{"sha": "123"}]

        processed_commits = [{"commit_hash": "123"}]
        failed_commits = []

        get_github_provider._fetch_commit_batch = mocker.AsyncMock(
            return_value=fake_batch
        )
        get_github_provider._process_commit_batch = mocker.AsyncMock(
            return_value=(processed_commits, failed_commits)
        )

        result = (
            await get_github_provider.get_and_process_commit_batch_from_remote_provider(
                httpx_client=mock_httpx_client,
                token="fake-token",
                repo_name="example/repo",
                batch_number=1,
            )
        )

        assert result[0] == processed_commits
        assert result[1] == failed_commits
        get_github_provider._fetch_commit_batch.assert_awaited_once()
        get_github_provider._process_commit_batch.assert_awaited_once_with(
            fake_batch, "example/repo"
        )

    async def test_get_and_process_commit_batch_with_failures(
        self, mocker, get_github_provider, mock_httpx_client
    ):
        fake_batch = [{"sha": "a"}, {"sha": "b"}]
        processed_commits = [{"commit_hash": "a"}]
        failed_commits = ["b"]

        get_github_provider._fetch_commit_batch = mocker.AsyncMock(
            return_value=fake_batch
        )
        get_github_provider._process_commit_batch = mocker.AsyncMock(
            return_value=(processed_commits, failed_commits)
        )

        result = (
            await get_github_provider.get_and_process_commit_batch_from_remote_provider(
                httpx_client=mock_httpx_client,
                token="fake-token",
                repo_name="example/repo",
                batch_number=2,
            )
        )

        assert result[0] == processed_commits
        assert result[1] == failed_commits
