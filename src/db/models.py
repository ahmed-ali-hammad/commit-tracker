from sqlalchemy import BIGINT, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Commit(Base):
    """
    ORM model representing a Git commits.
    """

    __tablename__ = "commit"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    commit_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    author_name: Mapped[str] = mapped_column(String(128), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    commit_date: Mapped[int] = mapped_column(BIGINT, nullable=False)  # Unix timestamp
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
