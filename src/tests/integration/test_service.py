import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert

from src.db.models import Commit
from src.domain.models import AuthorCommitSummary, CommitData, GroupedCommits


@pytest.mark.asyncio
class TestCommitService:
    async def test_retrieve_and_store_commits_success(
        self, mocker, commit_service_test_instance, test_db_session, raw_test_commits
    ):
        mock_get_and_process_commit_batch_from_remote_provider = mocker.AsyncMock(
            return_value=(raw_test_commits, [])
        )
        commit_service_test_instance.git_provider.get_and_process_commit_batch_from_remote_provider = (
            mock_get_and_process_commit_batch_from_remote_provider
        )

        await commit_service_test_instance.retrieve_and_store_commits(
            httpx_client=mocker.MagicMock(),
            token="Super Secure Token",
            repo_name="Coding",
        )

        result = await test_db_session.execute(
            select(func.count()).where(
                Commit.author_email.in_(["jasnell@gmail.com", "yagiz@nizipli.com"])
            )
        )
        assert result.scalar_one() == 3
        mock_get_and_process_commit_batch_from_remote_provider.assert_called()

    async def test_retrieve_and_store_commits_failure(
        self, mocker, commit_service_test_instance, test_db_session, caplog
    ):
        mock_get_and_process_commit_batch_from_remote_provider = mocker.AsyncMock(
            side_effect=Exception("client Error")
        )
        commit_service_test_instance.git_provider.get_and_process_commit_batch_from_remote_provider = (
            mock_get_and_process_commit_batch_from_remote_provider
        )

        await commit_service_test_instance.retrieve_and_store_commits(
            httpx_client=mocker.MagicMock(),
            token="Super Secure Token",
            repo_name="Coding",
        )

        result = await test_db_session.execute(select(func.count()).select_from(Commit))
        assert result.scalar_one() == 0

        assert "client Error" in caplog.text
        assert "Failed to fetch and store commits for batch" in caplog.text
        mock_get_and_process_commit_batch_from_remote_provider.assert_called()

    async def test_get_commits_by_author_full_name_success(
        self, commit_service_test_instance, create_dummpy_commits
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email(
                "Jake L."
            )
        )

        assert commits is not None
        assert isinstance(commits, list) and all(
            isinstance(commit, CommitData) for commit in commits
        )
        assert commits[0].author_name == "Jake L."
        assert commits[0].author_email == "jake@netops.dev"
        assert commits[0].commit_hash == "e5c66a7815e7f8d2354f6ffb8ec0aa7a3d15e3a7"
        assert commits[0].commit_message == "fix: handle large file streams in fs.read"

    async def test_get_commits_by_author_first_name_only_success(
        self, commit_service_test_instance, create_dummpy_commits
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email(
                "Emily"
            )
        )

        assert commits is not None
        assert isinstance(commits, list)
        assert commits[0].author_name == "Emily Tan"
        assert commits[0].author_email == "emily@tanworks.dev"
        assert commits[0].commit_hash == "9e0576ccab63d8b6e498f7f20a3ce187cdb0a7b6"
        assert (
            commits[0].commit_message == "refactor: consolidate internal buffer logic"
        )

    async def test_get_commits_by_author_last_name_only_success(
        self, commit_service_test_instance, create_dummpy_commits
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email(
                "Voss"
            )
        )

        assert commits is not None
        assert isinstance(commits, list)
        assert commits[0].author_name == "Anika Voss"
        assert commits[0].author_email == "anika@coderspace.dev"
        assert commits[0].commit_hash == "36f0ff24aef2587c94b3c3e7cfc758ce87dd88ef"
        assert commits[0].commit_message == "feat: allow custom encoding in readline"

    async def test_get_commits_by_author_email_success(
        self, commit_service_test_instance, create_dummpy_commits
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email(
                "ruy@vlt.sh"
            )
        )

        assert commits is not None
        assert isinstance(commits, list)
        assert commits[0].author_name == "Ruy Adorno"

    async def test_get_commits_by_author_part_of_email_success(
        self, commit_service_test_instance, create_dummpy_commits
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email(
                "tomhsu"
            )
        )

        assert commits is not None
        assert isinstance(commits, list)
        assert commits[0].author_name == "Tom Hsu"

    async def test_get_commits_with_empty_author_name_or_email(
        self, commit_service_test_instance
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email("")
        )
        assert isinstance(commits, list)
        assert commits == []

    async def test_get_commits_with_None_author_name_or_email(
        self, commit_service_test_instance
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email(None)
        )
        assert isinstance(commits, list)
        assert commits == []

    async def test_get_commits_with_invalid_author_name_or_email(
        self, commit_service_test_instance
    ):
        commits = (
            await commit_service_test_instance.get_commits_by_author_name_or_email(
                "NotFoundAuthor"
            )
        )
        assert commits == []

    async def test_get_commits_summary_grouped_by_author_success(
        self, commit_service_test_instance, create_dummpy_commits
    ):
        summary_data = (
            await commit_service_test_instance.get_commits_summary_grouped_by_author()
        )

        assert summary_data is not None
        assert isinstance(summary_data, list) and all(
            isinstance(item, AuthorCommitSummary) for item in summary_data
        )

        assert len(summary_data) == 20
        assert summary_data[0].author_name == "Lina B."
        assert summary_data[0].author_email == "lina@bugtrack.dev"
        assert summary_data[0].total_number_of_commits == 1

    async def test_get_commits_summary_grouped_by_author_more_commits_for_existing_author(
        self, commit_service_test_instance, create_dummpy_commits, test_db_session
    ):
        # Fetch the initial commit summary grouped by author
        summary_data_before = (
            await commit_service_test_instance.get_commits_summary_grouped_by_author()
        )

        # Prepare new commit data for an author that already exists in the database
        new_commits_to_add = [
            {
                "commit_hash": "23d4f6c7e9b82a5e57fb39d9fd8271cd7e78bda2",
                "author_name": "Natalie P.",
                "author_email": "natalie@np.io",
                "commit_message": "fix: resolve bug in user authentication",
                "commit_date": 1745707807,
                "repo_name": "nodejs/node",
            },
            {
                "commit_hash": "b798feb6c69d6e4372bfcbb7d2b5d8decd345b3e",
                "author_name": "Natalie P.",
                "author_email": "natalie@np.io",
                "commit_message": "feat: add new endpoint for user profile",
                "commit_date": 1745711807,
                "repo_name": "nodejs/node",
            },
        ]

        statement = insert(Commit).values(new_commits_to_add)
        statement = statement.on_duplicate_key_update(
            commit_hash=statement.inserted.commit_hash
        )  # Dummy update: this does nothing but satisfies MySQL
        await test_db_session.execute(statement)
        await test_db_session.commit()

        # Fetch the updated commit summary after the new commits are added
        summary_data_after = (
            await commit_service_test_instance.get_commits_summary_grouped_by_author()
        )

        # The number of authors in the summary should remain the same, but the commit count for the existing author should increase
        assert len(summary_data_before) == len(summary_data_after)

    async def test_get_start_timestamp(self, commit_service_test_instance):
        timestamp = await commit_service_test_instance._get_start_timestamp()
        assert isinstance(timestamp, int)

    async def test_get_commits_summary_grouped_by_author_more_commits_for_new_author(
        self, commit_service_test_instance, create_dummpy_commits, test_db_session
    ):
        # Fetch the initial commit summary grouped by author
        summary_data_before = (
            await commit_service_test_instance.get_commits_summary_grouped_by_author()
        )

        # Prepare new commit data for an author that already exists in the database
        new_commits_to_add = [
            {
                "commit_hash": "23d4f6c7e9b82a5e57fb39d9fd8271cd7e78bda2",
                "author_name": "New Aurhor",
                "author_email": "new.author@gmail.com",
                "commit_message": "fix: resolve bug in user authentication",
                "commit_date": 1745707807,
                "repo_name": "nodejs/node",
            },
            {
                "commit_hash": "b798feb6c69d6e4372bfcbb7d2b5d8decd345b3e",
                "author_name": "New Aurhor",
                "author_email": "natalie@np.io",
                "commit_message": "feat: add new endpoint for user profile",
                "commit_date": 1745711807,
                "repo_name": "nodejs/node",
            },
        ]

        statement = insert(Commit).values(new_commits_to_add)
        statement = statement.on_duplicate_key_update(
            commit_hash=statement.inserted.commit_hash
        )  # Dummy update: this does nothing but satisfies MySQL
        await test_db_session.execute(statement)
        await test_db_session.commit()

        # Fetch the updated commit summary after the new commits are added
        summary_data_after = (
            await commit_service_test_instance.get_commits_summary_grouped_by_author()
        )

        # The number of authors in the summary should remain the same, but the commit count for the existing author should increase
        assert len(summary_data_before) != len(summary_data_after)

    async def test_get_recent_commits_grouped_by_author(
        self, mocker, commit_service_test_instance, create_dummpy_commits
    ):
        mocker.patch(
            "src.domain.service.CommitService._get_start_timestamp",
            return_value=1745356960,
        )
        commits = (
            await commit_service_test_instance.get_recent_commits_grouped_by_author()
        )

        assert commits is not None
        assert isinstance(commits, list) and all(
            isinstance(commit, GroupedCommits) for commit in commits
        )

        assert len(commits) == 11

    async def test_get_recent_commits_grouped_by_author_only_one_commit_found(
        self,
        mocker,
        commit_service_test_instance,
        create_dummpy_commits,
    ):

        mocker.patch(
            "src.domain.service.CommitService._get_start_timestamp",
            return_value=1745788960,
        )
        commits = (
            await commit_service_test_instance.get_recent_commits_grouped_by_author()
        )

        assert commits is not None
        assert isinstance(commits, list) and all(
            isinstance(commit, GroupedCommits) for commit in commits
        )

        assert len(commits) == 1
