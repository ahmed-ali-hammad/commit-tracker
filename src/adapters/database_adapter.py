from typing import Dict, List

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.storage import CommitStorage
from src.db.models import Commit
from src.domain.models import AuthorCommitSummary, CommitData, GroupedCommits


class DatabaseStorage(CommitStorage):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_commit_batch(self, commit_batch: List[Dict]) -> None:
        """Saves a batch of commits"""
        statement = insert(Commit).values(commit_batch)
        statement = statement.on_duplicate_key_update(
            commit_hash=statement.inserted.commit_hash
        )  # Dummy update: this does nothing but satisfies MySQL
        await self.session.execute(statement)
        await self.session.commit()

    async def fetch_commits_by_author(self, author_identifier: str) -> List[CommitData]:
        """Get all commits by a partial match of author name or email."""
        if author_identifier is None or author_identifier == "":
            return []
        statement = select(Commit).where(
            or_(
                Commit.author_name.ilike(f"%{author_identifier}%"),
                Commit.author_email.ilike(f"%{author_identifier}%"),
            )
        )
        result = await self.session.execute(statement)
        orm_commits = result.scalars().all()

        return [CommitData.model_validate(c, from_attributes=True) for c in orm_commits]

    async def fetch_commit_summary_by_author(self) -> List[AuthorCommitSummary]:
        """Get commit count and latest commit per author."""
        statement = (
            select(
                Commit.author_name,
                Commit.author_email,
                func.count(Commit.id).label("total_number_of_commits"),
                func.max(Commit.commit_date).label("latest_commit_date"),
            )
            .group_by(Commit.author_name, Commit.author_email)
            .order_by(func.count(Commit.id).desc())
        )

        result = await self.session.execute(statement)
        rows = result.mappings().all()

        return [AuthorCommitSummary.model_validate(row) for row in rows]

    async def fetch_commits_since(self, start_date: int) -> List[GroupedCommits]:
        """Get all commits from a specific timestamp onward."""
        statement = (
            select(Commit)
            .where(Commit.commit_date >= start_date)
            .order_by(Commit.author_name, Commit.commit_date.desc())
        )
        result = await self.session.execute(statement)

        grouped = {}
        for commit in result.scalars():
            commit_data = CommitData.model_validate(commit, from_attributes=True)
            if commit_data.author_name not in grouped:
                grouped[commit_data.author_name] = GroupedCommits(
                    author_name=commit_data.author_name, commits=[]
                )
            grouped[commit_data.author_name].commits.append(commit_data)

        return list(grouped.values())
