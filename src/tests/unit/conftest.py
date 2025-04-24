import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def mock_async_db_session(mocker):
    session = mocker.MagicMock(spec=AsyncSession)
    yield session
