import pytest

from src.domain.models import AuthorCommitSummary, CommitData, GroupedCommits


@pytest.mark.asyncio
class TestCommitService:
    async def test_retrieve_and_store_commits_success(
        self, mocker, commit_service_test_instance
    ):
        # Dummpy return since we won't check data, just function calls
        mock_get_and_process_commit_batch_from_remote_provider = mocker.AsyncMock(
            return_value=([], [])
        )
        commit_service_test_instance.git_provider.get_and_process_commit_batch_from_remote_provider = (
            mock_get_and_process_commit_batch_from_remote_provider
        )

        mock_save_commit_batch = mocker.AsyncMock()
        commit_service_test_instance.storage.save_commit_batch = mock_save_commit_batch

        await commit_service_test_instance.retrieve_and_store_commits(
            httpx_client=mocker.MagicMock(),
            token="Super Secure Token",
            repo_name="Coding",
        )

        mock_get_and_process_commit_batch_from_remote_provider.assert_called()
        mock_save_commit_batch.assert_called()

    async def test_retrieve_and_store_commits_exception_raised_in_the_git_provider_call(
        self, mocker, commit_service_test_instance, caplog
    ):
        mock_get_and_process_commit_batch_from_remote_provider = mocker.AsyncMock(
            side_effect=Exception("client Error")
        )
        commit_service_test_instance.git_provider.get_and_process_commit_batch_from_remote_provider = (
            mock_get_and_process_commit_batch_from_remote_provider
        )

        mock_save_commit_batch = mocker.AsyncMock()
        commit_service_test_instance.storage.save_commit_batch = mock_save_commit_batch

        await commit_service_test_instance.retrieve_and_store_commits(
            httpx_client=mocker.MagicMock(),
            token="Super Secure Token",
            repo_name="Coding",
        )

        assert "client Error" in caplog.text
        assert "Failed to fetch and store commits for batch" in caplog.text
        mock_get_and_process_commit_batch_from_remote_provider.assert_called()
        mock_save_commit_batch.assert_not_called()

    async def test_retrieve_and_store_commits_exception_raised_in_save_commit_call(
        self, mocker, commit_service_test_instance, caplog
    ):
        mock_get_and_process_commit_batch_from_remote_provider = mocker.AsyncMock(
            return_value=([], [])
        )
        commit_service_test_instance.git_provider.get_and_process_commit_batch_from_remote_provider = (
            mock_get_and_process_commit_batch_from_remote_provider
        )

        mock_save_commit_batch = mocker.AsyncMock(side_effect=Exception("client Error"))
        commit_service_test_instance.storage.save_commit_batch = mock_save_commit_batch

        await commit_service_test_instance.retrieve_and_store_commits(
            httpx_client=mocker.MagicMock(),
            token="Super Secure Token",
            repo_name="Coding",
        )

        assert "client Error" in caplog.text
        assert "Failed to fetch and store commits for batch" in caplog.text
        mock_get_and_process_commit_batch_from_remote_provider.assert_called()
        mock_save_commit_batch.assert_called()

    async def test_get_commits_by_author_full_name_success(
        self, mocker, commit_service_test_instance
    ):
        mock_fetch_commits_by_author = mocker.AsyncMock()
        commit_service_test_instance.storage.fetch_commits_by_author = (
            mock_fetch_commits_by_author
        )

        author_identifier = "Jake L."

        await commit_service_test_instance.get_commits_by_author_name_or_email(
            author_identifier
        )

        mock_fetch_commits_by_author.assert_called_once_with(author_identifier)

    async def test_get_commits_by_author_full_name_database_exception(
        self, mocker, commit_service_test_instance
    ):
        mock_fetch_commits_by_author = mocker.AsyncMock(
            side_effect=Exception("Database Error")
        )
        commit_service_test_instance.storage.fetch_commits_by_author = (
            mock_fetch_commits_by_author
        )

        author_identifier = "Jake L."

        with pytest.raises(Exception, match="Database Error"):
            await commit_service_test_instance.get_commits_by_author_name_or_email(
                author_identifier
            )

        mock_fetch_commits_by_author.assert_called_once_with(author_identifier)

    async def test_get_commits_by_author_returns_expected_data(
        self, mocker, commit_service_test_instance
    ):
        dummy_commits = [
            CommitData(
                commit_hash="abc123",
                author_name="Jake",
                author_email="jake@example.com",
                commit_date=1234567890,
                repo_name="Repo",
                commit_message="Best Commit",
            )
        ]
        mock_fetch_commits_by_author = mocker.AsyncMock(return_value=dummy_commits)
        commit_service_test_instance.storage.fetch_commits_by_author = (
            mock_fetch_commits_by_author
        )

        result = await commit_service_test_instance.get_commits_by_author_name_or_email(
            "Jake"
        )

        assert result == dummy_commits
        mock_fetch_commits_by_author.assert_called_once_with("Jake")

    async def test_get_commits_summary_grouped_by_author_success(
        self, mocker, commit_service_test_instance
    ):

        mock_fetch_commit_summary_by_author = mocker.AsyncMock()
        commit_service_test_instance.storage.fetch_commit_summary_by_author = (
            mock_fetch_commit_summary_by_author
        )

        await commit_service_test_instance.get_commits_summary_grouped_by_author()

        mock_fetch_commit_summary_by_author.assert_called_once()

    async def test_get_commits_summary_grouped_by_author_exception(
        self, mocker, commit_service_test_instance
    ):

        mock_fetch_commit_summary_by_author = mocker.AsyncMock(
            side_effect=Exception("Database Error")
        )
        commit_service_test_instance.storage.fetch_commit_summary_by_author = (
            mock_fetch_commit_summary_by_author
        )

        with pytest.raises(Exception, match="Database Error"):
            await commit_service_test_instance.get_commits_summary_grouped_by_author()

        mock_fetch_commit_summary_by_author.assert_called_once()

    async def test_get_commits_summary_grouped_by_author_returns_expected_data(
        self, mocker, commit_service_test_instance
    ):
        dummy_data = [
            AuthorCommitSummary(
                author_name="Alice",
                author_email="alice@banana.com",
                total_number_of_commits=5,
                latest_commit_date=1745703803,
            ),
            AuthorCommitSummary(
                author_name="Bob",
                author_email="Bob@banana.com",
                total_number_of_commits=59,
                latest_commit_date=1745703833,
            ),
        ]
        mock_fetch_commit_summary_by_author = mocker.AsyncMock(return_value=dummy_data)
        commit_service_test_instance.storage.fetch_commit_summary_by_author = (
            mock_fetch_commit_summary_by_author
        )

        result = (
            await commit_service_test_instance.get_commits_summary_grouped_by_author()
        )

        assert result == dummy_data
        mock_fetch_commit_summary_by_author.assert_called_once()

    async def test_get_commits_summary_grouped_by_author_empty_list(
        self, mocker, commit_service_test_instance
    ):
        mock_fetch_commit_summary_by_author = mocker.AsyncMock(return_value=[])
        commit_service_test_instance.storage.fetch_commit_summary_by_author = (
            mock_fetch_commit_summary_by_author
        )

        result = (
            await commit_service_test_instance.get_commits_summary_grouped_by_author()
        )

        assert result == []
        mock_fetch_commit_summary_by_author.assert_called_once()

    async def test_group_commits_by_author(self, commit_service_test_instance):
        commits = [
            CommitData(
                commit_hash="abc123",
                author_name="Jake",
                author_email="jake@example.com",
                commit_date=1234567890,
                repo_name="Repo",
                commit_message="Best Commit",
            ),
            CommitData(
                commit_hash="def123",
                author_name="Damien",
                author_email="damien@example.com",
                commit_date=1234567890,
                repo_name="Repo",
                commit_message="Second Best Commit",
            ),
            CommitData(
                commit_hash="ghi123",
                author_name="Jake",
                author_email="jake@example.com",
                commit_date=1234567890,
                repo_name="Repo",
                commit_message="Second Best Commit",
            ),
        ]

        grouped_commits = await commit_service_test_instance._group_commits_by_author(
            commits
        )
        authors = {group.author_name: group for group in grouped_commits}

        assert isinstance(grouped_commits, list) and all(
            isinstance(grouped_commit, GroupedCommits)
            for grouped_commit in grouped_commits
        )
        assert len(grouped_commits) == 2
        assert "Jake" in authors
        assert "Damien" in authors
        assert len(authors["Jake"].commits) == 2
        assert len(authors["Damien"].commits) == 1

    async def test_group_commits_by_author_empty_list(
        self, commit_service_test_instance
    ):
        grouped_commits = await commit_service_test_instance._group_commits_by_author(
            []
        )
        assert grouped_commits == []

    async def test_group_commits_by_author_single_commit(
        self, commit_service_test_instance
    ):
        commits = [
            CommitData(
                commit_hash="abc123",
                author_name="Alex",
                author_email="alex@example.com",
                commit_date=1234567890,
                repo_name="Repo",
                commit_message="Initial commit",
            )
        ]
        grouped_commits = await commit_service_test_instance._group_commits_by_author(
            commits
        )

        assert len(grouped_commits) == 1
        assert grouped_commits[0].author_name == "Alex"
        assert len(grouped_commits[0].commits) == 1

    async def test_get_recent_commits_grouped_by_author(
        self, mocker, commit_service_test_instance
    ):
        mcok_get_start_timestamp = mocker.patch(
            "src.domain.service.CommitService._get_start_timestamp"
        )

        mock_group_commits_by_author = mocker.patch(
            "src.domain.service.CommitService._group_commits_by_author"
        )

        mock_fetch_commits_since = mocker.AsyncMock()
        commit_service_test_instance.storage.fetch_commits_since = (
            mock_fetch_commits_since
        )

        await commit_service_test_instance.get_recent_commits_grouped_by_author()

        mcok_get_start_timestamp.assert_called_once()
        mock_group_commits_by_author.assert_called_once()
        mock_fetch_commits_since.assert_called_once()

    async def test_get_recent_commits_grouped_by_author_returns_expected_data(
        self, mocker, commit_service_test_instance
    ):
        expected_grouped_commits = [GroupedCommits(author_name="Jake", commits=[])]

        mocker.patch(
            "src.domain.service.CommitService._get_start_timestamp",
            return_value=1234567890,
        )
        mock_fetch_commits_since = mocker.AsyncMock(return_value=[])
        commit_service_test_instance.storage.fetch_commits_since = (
            mock_fetch_commits_since
        )

        mock_group_commits_by_author = mocker.AsyncMock(
            return_value=expected_grouped_commits
        )
        commit_service_test_instance._group_commits_by_author = (
            mock_group_commits_by_author
        )

        result = (
            await commit_service_test_instance.get_recent_commits_grouped_by_author()
        )

        assert result == expected_grouped_commits

    async def test_get_recent_commits_grouped_by_author_with_custom_days_ago(
        self, mocker, commit_service_test_instance
    ):
        mock_get_start_timestamp = mocker.patch(
            "src.domain.service.CommitService._get_start_timestamp",
            return_value=1234567890,
        )

        mock_fetch_commits_since = mocker.AsyncMock(return_value=[])
        commit_service_test_instance.storage.fetch_commits_since = (
            mock_fetch_commits_since
        )

        mock_group_commits_by_author = mocker.AsyncMock(return_value=[])
        commit_service_test_instance._group_commits_by_author = (
            mock_group_commits_by_author
        )

        await commit_service_test_instance.get_recent_commits_grouped_by_author(
            days_ago=7
        )

        mock_get_start_timestamp.assert_called_once_with(7)

    async def test_get_recent_commits_grouped_by_author_fetch_commits_fails(
        self, mocker, commit_service_test_instance
    ):
        mocker.patch(
            "src.domain.service.CommitService._get_start_timestamp",
            return_value=1234567890,
        )

        mock_group_commits_by_author = mocker.patch(
            "src.domain.service.CommitService._group_commits_by_author"
        )

        commit_service_test_instance.storage.fetch_commits_since = mocker.AsyncMock(
            side_effect=Exception("DB failure")
        )

        with pytest.raises(Exception, match="DB failure"):
            await commit_service_test_instance.get_recent_commits_grouped_by_author()

        mock_group_commits_by_author.assert_not_called()
