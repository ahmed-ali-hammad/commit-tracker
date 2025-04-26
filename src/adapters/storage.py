from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class CommitStorage(ABC):
    @abstractmethod
    async def save_commit_batch(self, commit_batch: List[Dict]) -> int:
        pass

    @abstractmethod
    async def fetch_commits_by_author(self, author_identifier: str) -> List[Dict]:
        pass

    @abstractmethod
    async def fetch_commit_summary_by_author(self) -> List[Tuple]:
        pass

    @abstractmethod
    async def fetch_commits_since(self, start_date: int) -> List[Dict]:
        pass
