import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.database_adapter import DatabaseStorage
from src.domain.service import CommitService


@pytest_asyncio.fixture
async def mock_db_session(mocker):
    session = mocker.MagicMock(spec=AsyncSession)
    yield session


@pytest_asyncio.fixture
async def commit_service_test_instance(mocker, mock_db_session):
    """
    Provide an instance of the CommitService with a mocked git provider
    and a mocked database storage for testing purposes.
    """
    database_storage = DatabaseStorage(mock_db_session)
    commit_service = CommitService(database_storage, mocker.MagicMock())

    return commit_service
