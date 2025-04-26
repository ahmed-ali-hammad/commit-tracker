from typing import Dict, List, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.storage import CommitStorage
from src.db.models import Commit


class DatabaseStorage(CommitStorage):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_commit_batch(self, commit_batch: List[Dict]) -> None:
        """Saves a batch of commits"""
        if not commit_batch:
            return 0

        statement = insert(Commit).values(commit_batch)
        statement = statement.on_duplicate_key_update(
            commit_hash=statement.inserted.commit_hash
        )  # Dummy update: this does nothing but satisfies MySQL
        await self.session.execute(statement)
        await self.session.commit()

    async def fetch_commits_by_author(self, author_identifier: str) -> List[Dict]:
        """Get all commits by a partial match of author name or email."""
        statement = select(Commit).where(
            or_(
                Commit.author_name.ilike(f"%{author_identifier}%"),
                Commit.author_email.ilike(f"%{author_identifier}%"),
            )
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def fetch_commit_summary_by_author(self) -> List[Tuple]:
        """Get commit count and latest commit per author."""
        statement = (
            select(
                Commit.author_name,
                Commit.author_email,
                func.count(Commit.id).label("total_commits"),
                func.max(Commit.commit_date).label("latest_commit_date"),
            )
            .group_by(Commit.author_name, Commit.author_email)
            .order_by(func.count(Commit.id).desc())
        )

        result = await self.session.execute(statement)
        return result.all()

    async def fetch_commits_since(self, start_date: int) -> List[Dict]:
        """Get all commits from a specific timestamp onward."""
        statement = (
            select(Commit)
            .where(Commit.commit_date >= start_date)
            .order_by(Commit.author_name, Commit.commit_date.desc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()
