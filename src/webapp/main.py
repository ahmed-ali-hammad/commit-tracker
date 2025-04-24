import logging
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import DatabaseManager, check_db_connection
from src.utils import SingletonHttpx
from src.webapp.settings import Settings

_logger = logging.getLogger(__name__)


@lru_cache
def get_settings():
    """
    Loads and caches the application settings.

    Returns:
        Settings: The cached settings object.
    """
    return Settings()


@asynccontextmanager
async def life_span(app: FastAPI):
    # Initialize DB and Logging
    DatabaseManager(get_settings().DATABASE_URI)
    logging.basicConfig(
        level=get_settings().LOG_LEVEL,
        format="%(levelname)s:%(asctime)s: %(name)s: %(message)s",
    )
    _logger.info("Starting API service...")

    yield

    _logger.info("Shutting down API service...")
    await DatabaseManager._async_engine.dispose()
    await SingletonHttpx.close_httpx_client()
    _logger.info("Cleanup complete. Bye!")


app = FastAPI(title="Commit Tracker API", lifespan=life_span)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
async def health_check(session: AsyncSession = Depends(DatabaseManager.get_session)):
    """
    Endpoint that checks if the app and database are functioning.

    Args:
        db_sess (AsyncSession): The database session.

    Returns:
        dict: Health status of the application and database.
    """

    db_connection_status = await check_db_connection(session)

    if not db_connection_status:
        raise HTTPException(status_code=500, detail="Database connection failed")

    return {"status": "OK"}
