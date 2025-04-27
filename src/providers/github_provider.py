import logging
from typing import List, Tuple

import httpx

from src.domain.exceptions import DataTransformationError
from src.providers.git_providers import GitProvider
from src.providers.validator import GitHubCommitSchema

_logger = logging.getLogger(__name__)


class GitHubProvider(GitProvider):
    PER_BATCH_LIMIT = 100  # Max number of commits per Batch

    async def _fetch_commit_batch(
        self,
        httpx_client: httpx.AsyncClient,
        github_access_token: str,
        repo_name: str,
        batch_number: int,
    ) -> List[dict]:
        """Fetch a batch of commits from GitHub API."""

        url = f"https://api.github.com/repos/{repo_name}/commits"

        params = {"page": batch_number, "per_page": self.PER_BATCH_LIMIT}

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        response = await httpx_client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _transform_commit_data(self, commit_data: dict, repo_name: str) -> dict:
        """Transform GitHub API commit data into a standardized format."""
        try:
            validated = GitHubCommitSchema(**commit_data)
            return {
                "commit_hash": validated.sha,
                "author_name": validated.commit.author.name,
                "author_email": validated.commit.author.email,
                "commit_message": validated.commit.message,
                "commit_date": int(validated.commit.author.date.timestamp()),
                "repo_name": repo_name,
            }
        except Exception as e:
            raise DataTransformationError(
                f"Failed to transform commit data: {str(e)}"
            ) from e

    def _process_commit_batch(
        self, commits: List[dict], repo_name: str
    ) -> Tuple[List[dict], List[str]]:
        """Process a batch of commits, categorizing them into successful and failed."""
        successful_commits = []
        failed_commits = []

        for commit_data in commits:
            try:
                transformed = self._transform_commit_data(commit_data, repo_name)
                successful_commits.append(transformed)
            except DataTransformationError as e:
                _logger.warning(
                    f"Failed to process commit {commit_data.get('sha', 'unknown')}: {e}"
                )
                failed_commits.append(commit_data.get("sha", "unknown"))

        return successful_commits, failed_commits

    async def get_and_process_commit_batch_from_remote_provider(
        self,
        httpx_client: httpx.AsyncClient,
        github_access_token: str,
        repo_name: str,
        batch_number: int,
    ) -> Tuple[List[dict], List[str]]:
        """Retrieve and process a batch of commits from GitHub."""

        batch = await self._fetch_commit_batch(
            httpx_client, github_access_token, repo_name, batch_number
        )
        successful_commits, failed_commits = self._process_commit_batch(
            batch, repo_name
        )

        return successful_commits, failed_commits
