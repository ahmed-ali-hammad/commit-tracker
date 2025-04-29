from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

import httpx


class GitProvider(ABC):
    """
    Abstract base class for Git providers (GitHub, GitLab, Bitbucket).
    """

    @abstractmethod
    async def _fetch_commit_batch(
        self, httpx_client: httpx.AsyncClient, token: str, repo_name: str, page: int
    ) -> List[Dict]:
        pass

    @abstractmethod
    async def get_and_process_commit_batch_from_remote_provider(
        self,
        httpx_client: httpx.AsyncClient,
        token: str,
        repo_name: str,
        batch_number: int,
    ) -> Tuple[List[dict], List[str]]:
        pass
