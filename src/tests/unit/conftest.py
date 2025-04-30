import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.database_adapter import DatabaseStorage
from src.domain.service import CommitService
from src.providers.github_provider import GitHubProvider


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


@pytest_asyncio.fixture
async def get_github_provider():
    return GitHubProvider()


@pytest_asyncio.fixture
async def mock_httpx_client(mocker):
    client = mocker.AsyncMock()
    client.get = mocker.AsyncMock()
    return client


@pytest_asyncio.fixture
async def sample_raw_commit():
    return {
        "sha": "123abc",
        "commit": {
            "author": {
                "name": "Alice",
                "email": "alice@mango.com",
                "date": 1745703803,
            },
            "message": "Sample commit",
        },
    }
