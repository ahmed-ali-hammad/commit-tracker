import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx

from src.adapters.database_adapter import DatabaseStorage
from src.domain.models import CommitData
from src.providers.git_providers import GitProvider

_logger = logging.getLogger(__name__)


class CommitService:
    DEFAULT_REPO_NAME = "nodejs/node"
    DEFAULT_PAGE_RANGE = (1, 11)
    DEFAULT_RECENT_DAYS = 7

    def __init__(self, storage: DatabaseStorage, git_provider: GitProvider) -> None:
        self.storage = storage
        self.git_provider = git_provider

    async def retrieve_and_store_commits(
        self,
        httpx_client: httpx.AsyncClient,
        github_access_token: str,
        repo_name: str = DEFAULT_REPO_NAME,
        page_range: tuple[int, int] = DEFAULT_PAGE_RANGE,
    ) -> None:
        results = {"total_processed": 0, "pages_processed": 0, "failed_commits": 0}

        # Fetch all pages concurrently
        tasks = [
            self.git_provider.get_and_process_commit_batch_from_remote_provider(
                httpx_client, github_access_token, repo_name, page
            )
            for page in range(*page_range)
        ]
        commit_batches = await asyncio.gather(*tasks, return_exceptions=True)

        for batch_num, batch in enumerate(commit_batches, 1):
            if isinstance(batch, Exception):
                _logger.error(f"Error fetching page {batch_num}: {batch}")
                continue

            successful_commits_list, failed_commits_list = batch

            await self.storage.save_commit_batch(successful_commits_list)

            results["pages_processed"] += 1
            results["total_processed"] += len(successful_commits_list)
            results["failed_commits"] += len(failed_commits_list)

            _logger.info(
                f"Processed {len(successful_commits_list)} commits from page {batch_num} ({len(failed_commits_list)} failed)"
            )

    async def get_commits_by_author_name_or_email(
        self, author_identifier: str
    ) -> list[CommitData]:
        commits = await self.storage.fetch_commits_by_author(author_identifier)
        return commits

    async def get_commits_summary_grouped_by_author(self):
        grouped_data = await self.storage.fetch_commit_summary_by_author()

        return [
            {
                "author_name": author.author_name,
                "author_email": author.author_email,
                "total_number_of_commits": author.total_commits,
                "latest_commit_date": author.latest_commit_date,
            }
            for author in grouped_data
        ]

    def _get_start_date(self, days_ago: int = DEFAULT_RECENT_DAYS) -> int:
        """Calculate timestamp for filtering commits."""
        return int((datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp())

    def _group_commits_by_author(self, commits: list[CommitData]) -> dict:
        """Process raw commits into grouped structure."""
        grouped = defaultdict(list)
        for commit in commits:
            grouped[commit.author_name].append(
                {
                    "commit_hash": commit.commit_hash,
                    "commit_date": commit.commit_date,
                }
            )
        return grouped

    async def get_recent_commits_grouped_by_author(
        self, days_ago: int = 7
    ) -> list[dict]:
        """Composed method using the split components."""
        start_date = self._get_start_date(days_ago)
        commits = await self.storage.fetch_commits_since(start_date)
        grouped = self._group_commits_by_author(commits)

        return [
            {"author_name": author, "commits": commits}
            for author, commits in grouped.items()
        ]
