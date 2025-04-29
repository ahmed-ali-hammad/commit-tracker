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
async def commit_service_test_instance(mocker, test_db_session):
    """
    Provide an instance of the CommitService with a mocked git provider
    for testing purposes.
    """
    database_storage = DatabaseStorage(test_db_session)
    commit_service = CommitService(database_storage, mocker.MagicMock())

    return commit_service


@pytest_asyncio.fixture
def raw_test_commits():
    return [
        {
            "commit_hash": "c1b15a49be8cf4f14cfac3c2a8207e012b97bfd4",
            "author_name": "James M Snell",
            "author_email": "jasnell@gmail.com",
            "commit_message": "esm: graduate import.meta properties...",
            "commit_date": 1745512649,
            "repo_name": "nodejs/node",
        },
        {
            "commit_hash": "e0cf8ae62a28bf78c5e956d2a0de10bb7a57d2bf",
            "author_name": "Yagiz Nizipli",
            "author_email": "yagiz@nizipli.com",
            "commit_message": "url: improve canParse() performance...",
            "commit_date": 1745765549,
            "repo_name": "nodejs/node",
        },
        {
            "commit_hash": "647175ee0b8ca19d6f315216c879b1dc89ad2759",
            "author_name": "James M Snell",
            "author_email": "jasnell@gmail.com",
            "commit_message": "buffer: move SlowBuffer to EOL...",
            "commit_date": 1745506222,
            "repo_name": "nodejs/node",
        },
    ]
