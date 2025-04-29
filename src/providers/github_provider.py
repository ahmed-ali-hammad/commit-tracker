import logging
from typing import List, Tuple

import httpx
from pydantic import ValidationError

from src.providers.exceptions import GitProviderDataValidationError
from src.providers.git_providers import GitProvider
from src.providers.validator import GitHubCommitSchema

_logger = logging.getLogger(__name__)


class GitHubProvider(GitProvider):
    PER_BATCH_LIMIT = 100  # Max number of commits per Batch

    async def _fetch_commit_batch(
        self,
        httpx_client: httpx.AsyncClient,
        token: str,
        repo_name: str,
        batch_number: int,
    ) -> List[dict]:
        """
        Fetches a batch of commits from the GitHub API.

        Args:
            httpx_client (httpx.AsyncClient): HTTP client for making async requests.
            token (str): GitHub access token for authentication.
            repo_name (str): Name of the repository to fetch commits from.
            batch_number (int): The batch number to fetch.

        Returns:
            List[dict]: A list of raw commits.
        """

        url = f"https://api.github.com/repos/{repo_name}/commits"

        params = {"page": batch_number, "per_page": self.PER_BATCH_LIMIT}

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # We should really handle GitHub rate limiting (403 or 429), maybe using backoff library
        response = await httpx_client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    async def _parse_and_validate_commit(
        self, commit_data: dict, repo_name: str
    ) -> dict:
        """
        Verifies and extracts commit information from the raw GitHub API response.

        Args:
            commit_data (dict): Raw commit data from GitHub API.
            repo_name (str): Name of the repository.

        Returns:
            dict: Transformed commit data.

        Raises:
            GitProviderDataValidationError: If data validation fails.
        """
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
        except ValidationError as e:
            raise GitProviderDataValidationError(
                f"Failed to validate commit data for repo: '{repo_name}': {e}"
            ) from e

    async def _process_commit_batch(
        self, commits: List[dict], repo_name: str
    ) -> Tuple[List[dict], List[str]]:
        """
        Processes a batch of commits.

        Args:
            commits (List[dict]): List of raw commit data from the GitHub API.
            repo_name (str): Name of the repository.

        Returns:
            Tuple[List[dict], List[str]]: A tuple containing:
                - A list of successfully parsed commits.
                - A list of commit SHAs that failed to process.
        """
        successful_commits = []
        failed_commits = []

        for commit_data in commits:
            try:
                transformed = await self._parse_and_validate_commit(
                    commit_data, repo_name
                )
                successful_commits.append(transformed)
            except GitProviderDataValidationError as e:
                _logger.warning(
                    f"Failed to process commit {commit_data.get('sha', 'unknown')}: {e}"
                )
                failed_commits.append(commit_data.get("sha", "unknown"))

        return successful_commits, failed_commits

    async def get_and_process_commit_batch_from_remote_provider(
        self,
        httpx_client: httpx.AsyncClient,
        token: str,
        repo_name: str,
        batch_number: int,
    ) -> Tuple[List[dict], List[str]]:
        """
        Retrieves and processes a batch of commits from GitHub.

        Args:
            httpx_client (httpx.AsyncClient): HTTP client for making async requests.
            token (str): GitHub access token for authentication.
            repo_name (str): Name of the repository to fetch commits from.
            batch_number (int): The batch number to fetch and process.

        Returns:
            Tuple[List[dict], List[str]]: A tuple containing:
                - A list of successfully processed commits.
                - A list of commit SHAs that failed to process.
        """
        batch = await self._fetch_commit_batch(
            httpx_client, token, repo_name, batch_number
        )
        successful_commits, failed_commits = await self._process_commit_batch(
            batch, repo_name
        )

        return successful_commits, failed_commits
