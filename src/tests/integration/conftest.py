from unittest.mock import MagicMock

import pytest_asyncio
from sqlalchemy.dialects.mysql import insert

from src.adapters.database_adapter import DatabaseStorage
from src.db.models import Commit
from src.domain.service import CommitService
from src.tests.integration.dummpy_commits_data import test_commits
from src.tests.integration.helpers import get_session_test


@pytest_asyncio.fixture
async def test_db_session():
    async for session in get_session_test():
        yield session


@pytest_asyncio.fixture
async def create_dummpy_commits(test_db_session):
    statement = insert(Commit).values(test_commits)
    await test_db_session.execute(statement)
    await test_db_session.commit()


@pytest_asyncio.fixture
async def commit_service_test_instance(test_db_session):
    """
    Provide an instance of the CommitService with a mocked git provider
    for testing purposes.
    """
    database_storage = DatabaseStorage(test_db_session)

    commit_service = CommitService(database_storage, MagicMock())
    return commit_service
