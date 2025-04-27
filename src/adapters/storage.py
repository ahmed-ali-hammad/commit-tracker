from abc import ABC, abstractmethod
from typing import Dict, List

from src.domain.models import AuthorCommitSummary, CommitData


class CommitStorage(ABC):
    @abstractmethod
    async def save_commit_batch(self, commit_batch: List[Dict]) -> None:
        pass

    @abstractmethod
    async def fetch_commits_by_author(self, author_identifier: str) -> List[CommitData]:
        pass

    @abstractmethod
    async def fetch_commit_summary_by_author(self) -> List[AuthorCommitSummary]:
        pass

    @abstractmethod
    async def fetch_commits_since(self, start_date: int) -> List[CommitData]:
        pass
