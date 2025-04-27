from datetime import datetime
from typing import List

from pydantic import BaseModel


class CommitData(BaseModel):
    commit_hash: str
    commit_date: datetime
    author_name: str
    author_email: str
    repo_name: str
    commit_message: str


class AuthorCommitSummary(BaseModel):
    author_name: str
    author_email: str
    total_number_of_commits: int
    latest_commit_date: datetime


class GroupedCommits(BaseModel):
    author_name: str
    commits: List[CommitData]
