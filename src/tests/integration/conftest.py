import pytest_asyncio
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.models import Base, Commit
from src.tests.integration.dummpy_commits_data import test_commits
from src.webapp.settings import Settings


def get_settings_test():
    return Settings(
        GITHUB_API_URL="https://github-api-test-only.de",
        GITHUB_ACCESS_TOKEN="dummy-token",
        DATABASE_USER="db_user_test",
        DATABASE_PASSWORD="Zds5DuF6TLbZexOZHjP",
        DATABASE_HOST="commit-tracker-db-test",
        DATABASE_PORT="3306",
        DATABASE_NAME="commit_history",
    )


@pytest_asyncio.fixture
async def db_session_test():
    engine = create_async_engine(get_settings_test().ASYNC_DATABASE_URI)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def create_dummpy_commits(db_session_test):
    statement = insert(Commit).values(test_commits)
    await db_session_test.execute(statement)
    await db_session_test.commit()
