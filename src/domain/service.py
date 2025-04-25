import asyncio
import logging

import httpx
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Commit
from src.domain.validator import GitHubCommit

_logger = logging.getLogger(__name__)


class CommitService:
    @staticmethod
    async def fetch_commit_page(
        httpx_client: httpx.AsyncClient, github_access_token, page: int
    ) -> list[dict]:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = (
            f"https://api.github.com/repos/nodejs/node/commits?per_page=100&page={page}"
        )
        response = await httpx_client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def process_commit_batch(commits: list) -> tuple[list, list]:
        successful_commits = []
        failed_commits = []

        for commit_data in commits:
            try:
                validated = GitHubCommit(**commit_data)
                successful_commits.append(
                    {
                        "commit_hash": validated.sha,
                        "author_name": validated.commit.author.name,
                        "author_email": validated.commit.author.email,
                        "commit_message": validated.commit.message,
                        "commit_date": int(validated.commit.author.date.timestamp()),
                        "repo_name": "nodejs/node",
                    }
                )
            except Exception as e:
                _logger.warning(f"Error processing commit: {e}")
                failed_commits.append(commit_data.get("sha", "unknown"))

        return successful_commits, failed_commits

    @staticmethod
    async def save_commits_batch(session: AsyncSession, commit_batch: list):
        if not commit_batch:
            return

        stmt = insert(Commit).values(commit_batch)
        stmt = stmt.on_duplicate_key_update(
            commit_hash=stmt.inserted.commit_hash
        )  # Dummy update: this does nothing but satisfies MySQL
        await session.execute(stmt)
        return len(commit_batch)

    @staticmethod
    async def retrieve_and_store_commits(
        session: AsyncSession, httpx_client: httpx.AsyncClient, github_access_token: str
    ) -> dict:
        results = {"total_processed": 0, "pages_processed": 0, "failed_commits": 0}

        # Fetch all pages concurrently
        pages = range(1, 11)
        tasks = [
            CommitService.fetch_commit_page(httpx_client, github_access_token, page)
            for page in pages
        ]
        pages_data = await asyncio.gather(*tasks, return_exceptions=True)

        for page_num, page_result in enumerate(pages_data, 1):
            if isinstance(page_result, Exception):
                _logger.error(f"Error fetching page {page_num}: {page_result}")
                continue

            commit_batch, failed = CommitService.process_commit_batch(page_result)
            processed = await CommitService.save_commits_batch(session, commit_batch)

            results["total_processed"] += processed
            results["pages_processed"] += 1
            results["failed_commits"] += len(failed)

            _logger.info(
                f"Processed {processed} commits from page {page_num} ({len(failed)} failed)"
            )

        await session.commit()
        return results
