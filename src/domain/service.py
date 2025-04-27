import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx

from src.adapters.storage import CommitStorage
from src.db.models import Commit
from src.domain.validator import GitHubCommit
from src.git_providers import GitProvider

_logger = logging.getLogger(__name__)


class CommitService:
    DEFAULT_REPO_NAME = "nodejs/node"
    DEFAULT_PAGE_RANGE = (1, 11)
    DEFAULT_RECENT_DAYS = 7

    def __init__(self, storage: CommitStorage, git_provider: GitProvider):
        self.storage = storage
        self.git_provider = git_provider

    @staticmethod
    def _transform_commit_data(
        commit_data: dict, repo_name: str = DEFAULT_REPO_NAME
    ) -> dict:
        """Transform raw commit data into storage format."""
        validated = GitHubCommit(**commit_data)
        return {
            "commit_hash": validated.sha,
            "author_name": validated.commit.author.name,
            "author_email": validated.commit.author.email,
            "commit_message": validated.commit.message,
            "commit_date": int(validated.commit.author.date.timestamp()),
            "repo_name": repo_name,
        }

    @staticmethod
    def _process_commit_batch(
        commits: list, repo_name: str = DEFAULT_REPO_NAME
    ) -> tuple[list, list]:
        successful_commits = []
        failed_commits = []

        for commit_data in commits:
            try:
                transformed = CommitService._transform_commit_data(
                    commit_data, repo_name
                )
                successful_commits.append(transformed)
            except Exception as e:
                _logger.warning(f"Error processing commit: {e}")
                failed_commits.append(commit_data.get("sha", "unknown"))

        return successful_commits, failed_commits

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
            self.git_provider._fetch_commit_batch(
                httpx_client, github_access_token, repo_name, page
            )
            for page in range(*page_range)
        ]
        pages_data = await asyncio.gather(*tasks, return_exceptions=True)

        for page_num, page_result in enumerate(pages_data, 1):
            if isinstance(page_result, Exception):
                _logger.error(f"Error fetching page {page_num}: {page_result}")
                continue

            commit_batch, failed = self._process_commit_batch(page_result)
            await self.storage.save_commit_batch(commit_batch)

            results["pages_processed"] += 1
            results["total_processed"] += len(commit_batch)
            results["failed_commits"] += len(failed)

            _logger.info(
                f"Processed {len(commit_batch)} commits from page {page_num} ({len(failed)} failed)"
            )

    async def get_commits_by_author_name_or_email(self, author_identifier):
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

    def _group_commits_by_author(self, commits: list[Commit]) -> dict:
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

    async def get_recent_commits_grouped_by_author(self, days_ago: int = 7) -> dict:
        """Composed method using the split components."""
        start_date = self._get_start_date(days_ago)
        commits = await self.storage.fetch_commits_since(start_date)
        grouped = self._group_commits_by_author(commits)

        return [
            {"author_name": author, "commits": commits}
            for author, commits in grouped.items()
        ]
