import logging
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.sql import text

_logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages the configuration and sessions setup for the database.
    """

    _instance = None
    _async_engine: Optional[AsyncEngine] = None

    def __new__(cls, database_uri: str):
        if not hasattr(cls, "instance"):
            cls.instance = super(DatabaseManager, cls).__new__(cls)
            cls._async_engine = create_async_engine(url=database_uri, echo=False)
        return cls.instance

    @staticmethod
    async def get_session() -> AsyncIterator[AsyncSession]:
        """
        Initializes an asynchronous database session using SQLAlchemy's
        async engine and sessionmaker. It yields an `AsyncSession` instance, which can
        be used to interact with the database. The session is automatically closed
        after usage.

        Returns:
            AsyncSession: database session.
        """
        Session = async_sessionmaker(
            bind=DatabaseManager._async_engine, expire_on_commit=False
        )

        async with Session() as session:
            yield session

    @classmethod
    async def dispose_engine(cls) -> None:
        """
        Disposes the current async engine.

        This method is used to safely close and release resources associated
        with the current async engine.
        """
        if cls._async_engine is not None:
            _logger.info("Disposing of the current async engine.")
            await cls._async_engine.dispose()
        cls._async_engine = None


async def check_db_connection(session: AsyncSession) -> bool:
    """
    Simple check for database connection using a SELECT query.

    Args:
        session (AsyncSession): The database session.

    Returns:
        bool: True if the DB is reachable, False otherwise.
    """
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        _logger.error(
            f"Database connection error: {e}",
            exc_info=True,
        )
        return False
