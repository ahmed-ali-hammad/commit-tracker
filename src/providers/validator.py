from datetime import datetime

from pydantic import BaseModel


class CommitAuthor(BaseModel):
    name: str
    email: str
    date: datetime


class CommitInfo(BaseModel):
    author: CommitAuthor
    message: str


class GitHubCommitSchema(BaseModel):
    sha: str
    commit: CommitInfo
