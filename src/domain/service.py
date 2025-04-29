import logging
from datetime import datetime, timedelta, timezone
from typing import List

import httpx

from src.adapters.database_adapter import DatabaseStorage
from src.domain.models import AuthorCommitSummary, CommitData, GroupedCommits
from src.providers.git_providers import GitProvider

_logger = logging.getLogger(__name__)


class CommitService:
    """
    Service class for handling commit-related operations.
    """

    DEFAULT_REPO_NAME = "nodejs/node"
    DEFAULT_BATCH_RANGE = (1, 11)
    DEFAULT_RECENT_DAYS = 7

    def __init__(self, storage: DatabaseStorage, git_provider: GitProvider) -> None:
        self.storage = storage
        self.git_provider = git_provider

    async def retrieve_and_store_commits(
        self,
        httpx_client: httpx.AsyncClient,
        token: str,
        repo_name: str = DEFAULT_REPO_NAME,
        batch_range: tuple[int, int] = DEFAULT_BATCH_RANGE,
    ) -> None:
        """
        Fetches and stores commit batches from a remote Git provider.

        Args:
            httpx_client (httpx.AsyncClient): HTTP client for async requests.
            token (str): An access token for the git_provider.
            repo_name (str, optional): Repository name. Defaults to DEFAULT_REPO_NAME.
            batch_range (tuple[int, int], optional): Batch range to fetch. Defaults to DEFAULT_BATCH_RANGE.
        """
        results = {"total_processed": 0, "batches_processed": 0, "failed_commits": 0}

        for batch in range(*batch_range):
            try:
                successful_commits, failed_commits = (
                    await self.git_provider.get_and_process_commit_batch_from_remote_provider(
                        httpx_client=httpx_client,
                        token=token,
                        repo_name=repo_name,
                        batch_number=batch,
                    )
                )
                await self.storage.save_commit_batch(successful_commits)

                results["batches_processed"] += 1
                results["total_processed"] += len(successful_commits)
                results["failed_commits"] += len(failed_commits)

                _logger.info(
                    f"batch: {batch} — Processed: {len(successful_commits)}, Failed: {len(failed_commits)}"
                )

            except Exception as ex:
                _logger.error(
                    f"Failed to fetch and store commits for batch: {batch}. Exception: {ex}"
                )
        _logger.info(
            f"Total commits retrieved: {results['total_processed'] + results['failed_commits']} — "
            f"Successfully processed: {results['total_processed']}, "
            f"Failed to process: {results['failed_commits']}"
        )

    async def get_commits_by_author_name_or_email(
        self, author_identifier: str
    ) -> list[CommitData]:
        """
        Retrieves commits by author name or email.

        Args:
            author_identifier (str): Author's name or email.

        Returns:
            list[CommitData]: List of matching commits.
        """
        commits = await self.storage.fetch_commits_by_author(author_identifier)
        return commits

    async def get_commits_summary_grouped_by_author(self) -> list[AuthorCommitSummary]:
        """
        Returns a summary date of commits grouped by author.

        Returns:
            list[AuthorCommitSummary]: Summary data per author.
        """
        summary_data = await self.storage.fetch_commit_summary_by_author()
        return summary_data

    async def _get_start_timestamp(self, days_ago: int = DEFAULT_RECENT_DAYS) -> int:
        """
        Calculates the unix timestamp for a given number of days ago.

        Args:
            days_ago (int, optional): Number of days ago to calculate the timestamp for.
                Defaults to DEFAULT_RECENT_DAYS.

        Returns:
            int: The unix timestamp for the calculated date.
        """
        return int((datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp())

    async def _group_commits_by_author(
        self,
        commits: List[CommitData],
    ) -> List[GroupedCommits]:
        """
        Groups commits by author name.

        Args:
            commits (List[CommitData]): List of validated commit data.

        Returns:
            List[GroupedCommits]: Commits grouped by author.
        """
        grouped = {}
        for commit in commits:
            if commit.author_name not in grouped:
                grouped[commit.author_name] = GroupedCommits(
                    author_name=commit.author_name, commits=[]
                )
            grouped[commit.author_name].commits.append(commit)
        return list(grouped.values())

    async def get_recent_commits_grouped_by_author(
        self, days_ago: int = DEFAULT_RECENT_DAYS
    ) -> list[GroupedCommits]:
        """
        Retrieves recent commits grouped by author.

        Args:
            days_ago (int, optional): Number of days ago to start fetching commits.
                Defaults to DEFAULT_RECENT_DAYS.

        Returns:
            list[GroupedCommits]: List of commits grouped by author.
        """
        start_date = await self._get_start_timestamp(days_ago)
        commits = await self.storage.fetch_commits_since(start_date)
        grouped_commits = await self._group_commits_by_author(commits=commits)
        return grouped_commits
