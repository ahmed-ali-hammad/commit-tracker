import logging
from datetime import datetime, timedelta, timezone

import httpx

from src.adapters.database_adapter import DatabaseStorage
from src.domain.models import AuthorCommitSummary, CommitData, GroupedCommits
from src.providers.git_providers import GitProvider

_logger = logging.getLogger(__name__)


class CommitService:
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
        results = {"total_processed": 0, "batches_processed": 0, "failed_commits": 0}

        for batch in range(*batch_range):
            try:
                successful_commits, failed_commits = (
                    await self.git_provider.get_and_process_commit_batch_from_remote_provider(
                        httpx_client=httpx_client,
                        github_access_token=token,
                        repo_name=repo_name,
                        batch_number=batch,
                    )
                )
                await self.storage.save_commit_batch(successful_commits)

                results["batches_processed"] += 1
                results["total_processed"] += len(successful_commits)
                results["failed_commits"] += len(failed_commits)

                _logger.info(
                    f"batch {batch} — Processed: {len(successful_commits)}, Failed: {len(failed_commits)}"
                )

            except Exception as ex:
                _logger.error(f"Error fetching batch {batch}: {ex}")
        _logger.info(
            f"Total commits retrieved: {results['total_processed'] + results['failed_commits']} — "
            f"Successfully processed: {results['total_processed']}, "
            f"Failed to process: {results['failed_commits']}"
        )

    async def get_commits_by_author_name_or_email(
        self, author_identifier: str
    ) -> list[CommitData]:
        commits = await self.storage.fetch_commits_by_author(author_identifier)
        return commits

    async def get_commits_summary_grouped_by_author(self) -> list[AuthorCommitSummary]:
        summary_data = await self.storage.fetch_commit_summary_by_author()
        return summary_data

    def _get_start_date(self, days_ago: int = DEFAULT_RECENT_DAYS) -> int:
        """Calculate timestamp for filtering commits."""
        return int((datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp())

    async def get_recent_commits_grouped_by_author(
        self, days_ago: int = 7
    ) -> list[GroupedCommits]:
        start_date = self._get_start_date(days_ago)
        commits = await self.storage.fetch_commits_since(start_date)
        return commits
