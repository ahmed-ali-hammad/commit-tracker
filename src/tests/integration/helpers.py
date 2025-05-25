from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.models import Base
from src.webapp.settings import Settings


def get_settings_test():
    """
    A helper function that returns the test-specific settings for the application.
    """
    return Settings(
        GITHUB_ACCESS_TOKEN="dummy-token",
        DATABASE_USER="db_user_test",
        DATABASE_PASSWORD="Zds5DuF6TLbZexOZHjP",
        DATABASE_HOST="commit-tracker-db-test",
        DATABASE_PORT="3306",
        DATABASE_NAME="commit_history",
    )


async def get_session_test():
    """
    A helper function for use in fixtures or dependency overrides. It creates the necessary
    tables/session for testing and ensures that the database is cleaned up after the test
    by dropping the tables and disposing of the engine.
    """
    engine = create_async_engine(get_settings_test().ASYNC_DATABASE_URI)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
