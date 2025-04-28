"""
Dependency Injection container.
Centralizes factory functions for clean dependency management.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.database_adapter import DatabaseStorage
from src.adapters.storage import CommitStorage
from src.db.main import DatabaseManager
from src.domain.service import CommitService
from src.providers.github_provider import GitHubProvider, GitProvider


def get_storage(
    session: AsyncSession = Depends(DatabaseManager.get_session),
) -> CommitStorage:
    """
    Creates and returns a CommitStorage instance.
    This factory function creates a database-backed storage adapter configured with
    an active database session.

    Args:
        session: database session.

    Returns:
        CommitStorage: A DatabaseStorage instance implementing the CommitStorage interface.
    """
    return DatabaseStorage(session)


def get_git_provider() -> GitHubProvider:
    """Factory function that provides a Git provider.

    Returns:
        GitProvider: a Git provider instance.

    """
    return GitHubProvider()


def get_commit_service(
    storage: DatabaseStorage = Depends(get_storage),
    git_provider: GitProvider = Depends(get_git_provider),
) -> CommitService:
    """
    Creates a CommitService instance with a configured storage and git_provider.

    Args:
        storage: CommitStorage instance
        git_provider: GitProvider instance

    Returns:
        Configured CommitService ready for use
    """
    return CommitService(storage=storage, git_provider=git_provider)
