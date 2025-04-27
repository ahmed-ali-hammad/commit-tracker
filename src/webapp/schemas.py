from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator


class StatusResponse(BaseModel):
    status: str


class CommitDetailResponse(BaseModel):
    author_name: str
    commit_hash: str
    author_email: str
    commit_message: str
    commit_date: datetime
    repo_name: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("commit_date", mode="before")
    @classmethod
    def convert_unix_to_datetime(cls, v):
        if isinstance(v, int):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v


class AuthorCommitStatsResponse(BaseModel):
    author_name: str
    author_email: str
    total_number_of_commits: int
    latest_commit_date: datetime

    @field_validator("latest_commit_date", mode="before")
    @classmethod
    def convert_unix_to_datetime(cls, v):
        if isinstance(v, int):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v


class CommitSummary(BaseModel):
    commit_hash: str
    commit_date: datetime

    @field_validator("commit_date", mode="before")
    @classmethod
    def convert_unix_to_datetime(cls, v):
        if isinstance(v, int):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v


class AuthorCommitsListResponse(BaseModel):
    author_name: str
    commits: List[CommitSummary]
