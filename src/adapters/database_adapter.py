from typing import Dict, List

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.storage import CommitStorage
from src.db.models import Commit
from src.domain.models import AuthorCommitSummary, CommitData, GroupedCommits


class DatabaseStorage(CommitStorage):
    """
    An asynchronous implementation of `CommitStorage` that interacts with a SQL database
    using SQLAlchemy to store and retrieve commit-related data.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the `DatabaseStorage` with an asynchronous session.

        Args:
            session (AsyncSession): database session.
        """
        self.session = session

    async def save_commit_batch(self, commit_batch: List[Dict]) -> None:
        """
        Saves a batch of commits into the database using a bulk insert operation.
        If a duplicate commit hash is encountered, the insert is silently ignored (no-op update).

        Args:
            commit_batch (List[Dict]): A list of commit data dictionaries to insert.

        Raw SQL:
            INSERT INTO commit(...) VALUES(...) ON DUPLICATE KEY UPDATE commit_hash = VALUES(commit_hash);
        """
        statement = insert(Commit).values(commit_batch)
        statement = statement.on_duplicate_key_update(
            commit_hash=statement.inserted.commit_hash
        )  # Dummy update: this does nothing but satisfies MySQL
        await self.session.execute(statement)
        await self.session.commit()

    async def fetch_commits_by_author(self, author_identifier: str) -> List[CommitData]:
        """
        Retrieves all commits that partially match the given author name or email.

        Args:
            author_identifier (str): A substring to match against author name or email.

        Returns:
            List[CommitData]: A list of commit records that match the author identifier.

        Raw SQL:
            SELECT * FROM commit
            WHERE
                (commits.author_name LIKE CONCAT('%', ?, '%') OR commits.author_email LIKE CONCAT('%', ?, '%'));
        """
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
        """
        Retrieves a summary data of commits grouped by author

        Returns:
            List[AuthorCommitSummary]: A list of summary records for each author.
        Raw SQL:
            SELECT
                author_name, author_email, COUNT(id) AS total_number_of_commits, MAX(commit_date) AS latest_commit_date
            FROM
                commits
            GROUP BY
                author_name, author_email
            ORDER BY
                COUNT(id) DESC
        """
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
        """
        Retrieves all commits from a specific timestamp onward, grouped by author.

        Args:
            start_date (int): A Unix timestamp. Only commits after this time will be included.

        Returns:
            List[GroupedCommits]: A list of authors, each with a list of their commits.
        Raw SQL:
            SELECT  * FROM commits WHERE commit_date >= %(start_date)s
            ORDER BY author_name ASC, commit_date DESC
        """
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
