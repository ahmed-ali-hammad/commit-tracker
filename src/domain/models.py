from datetime import datetime

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
    total_commits: int
    latest_commit_date: datetime
