from abc import ABC, abstractmethod
from typing import Dict, List

import httpx


class GitProvider(ABC):
    @abstractmethod
    async def _fetch_commit_batch(
        httpx_client: httpx.AsyncClient, token: str, page: int
    ) -> List[Dict]:
        pass


class GitLabProvider(GitProvider):
    pass


class BitbucketProvider(GitProvider):
    pass


class GitHubProvider(GitProvider):
    @staticmethod
    async def _fetch_commit_batch(
        httpx_client: httpx.AsyncClient,
        github_access_token: str,
        repo_name: str,
        page: int,
    ) -> list[dict]:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        per_page = 100
        url = f"https://api.github.com/repos/{repo_name}/commits"

        params = {"page": page, "per_page": per_page}
        response = await httpx_client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
