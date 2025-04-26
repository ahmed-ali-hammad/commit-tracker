import logging
from contextlib import asynccontextmanager
from functools import lru_cache

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import DatabaseManager, check_db_connection
from src.domain.service import CommitService
from src.utils import SingletonHttpx
from src.webapp.dependencies import get_commit_service
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
    DatabaseManager(get_settings().ASYNC_DATABASE_URI)
    logging.basicConfig(
        level=get_settings().LOG_LEVEL,
        format="%(levelname)s:%(asctime)s: %(name)s: %(message)s",
    )
    _logger.info("Starting API service...")

    yield

    _logger.info("Shutting down API service...")
    await DatabaseManager.dispose_engine()
    await SingletonHttpx.close_httpx_client()
    _logger.info("Cleanup complete. Bye!")


app = FastAPI(title="Commit Tracker API", lifespan=life_span)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
async def health_check(
    session: AsyncSession = Depends(DatabaseManager.get_session),
) -> dict:
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


@app.post(
    "/commits/trigger-fetch",
    status_code=status.HTTP_200_OK,
)
async def trigger_commit_fetch(
    background_tasks: BackgroundTasks,
    httpx_client: httpx.AsyncClient = Depends(SingletonHttpx.get_httpx_client),
    settings: Settings = Depends(get_settings),
    commit_service: CommitService = Depends(get_commit_service),
) -> dict:
    """
    Triggers a background task to fetch and stores the latest 1000 commits.
    Returns immediately while processing continues in background.

    Returns:
        dict: A status message indicating the operation was successful.
    """
    try:
        background_tasks.add_task(
            commit_service.retrieve_and_store_commits,
            httpx_client=httpx_client,
            github_access_token=settings.GITHUB_ACCESS_TOKEN,
        )
        _logger.info("Background task for commit fetch successfully scheduled.")
        return {"status": "Processing started in background"}
    except Exception as ex:
        _logger.error(
            f"Failed to schedule background commit fetch task. Exception: {ex}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong",
        )


@app.get(
    "/commits/by-author/{author_identifier}",
    status_code=status.HTTP_200_OK,
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "Commits not found for the author"},
    },
)
async def get_commits_by_author(
    author_identifier: str,
    commit_service=Depends(get_commit_service),
):
    """
    Retrieve a list of commits for a given author based on their name or email.

    Returns:
        - HTTP 200: A list of commits for the given author.
        - HTTP 404: If no commits are found for the given author.
        - HTTP 500: If an internal error occurs while retrieving the commits.
    """
    _logger.info(f"Retrieving commits for author: '{author_identifier}'")
    try:
        # Get commits by author identifier (name or email)
        commits = await commit_service.get_commits_by_author_name_or_email(
            author_identifier
        )
    except Exception as ex:
        _logger.error(
            f"Error while retrieving commits for '{author_identifier}': {ex}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong",
        )

    if not commits:
        _logger.info(f"No commits found for author: '{author_identifier}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No commits found for the author: {author_identifier}",
        )

    return commits


@app.get(
    "/commits/authors/summary",
    status_code=status.HTTP_200_OK,
)
async def get_aggregated_commits_data_by_author(
    commit_service=Depends(get_commit_service),
):
    """
    Retrieves aggregated commit data grouped by author.

    This endpoint fetches the total number of commits and the latest commit date
    for each author in the database.

    Returns:
        - HTTP 200: A dictionary containing a list of authors with their aggregated commit data
        - HTTP 500: If an internal error occurs.

    """
    try:
        aggregated_commits = (
            await commit_service.get_commits_summary_grouped_by_author()
        )
        return aggregated_commits
    except Exception as ex:
        _logger.error(
            f"Error while retrieving aggregated commit data. Exception: {ex}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong",
        )


@app.get(
    "/commits/authors/recent",
    status_code=status.HTTP_200_OK,
)
async def get_commits_list_grouped_by_author_for_last_week(
    commit_service=Depends(get_commit_service),
):
    """
    Retrieves a list of commits grouped by author for the last 7 days.
    Each author will have a list of their commits, including commit hash and date.

    Returns:
        - HTTP 200: A list of dictionaries containing the recent commits.
        - HTTP 500: If an internal error occurs.
    """
    try:
        commits = await commit_service.get_recent_commits_grouped_by_author()
        return commits
    except Exception as ex:
        _logger.error(
            f"Error while retrieving recent commit list. Exception: {ex}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong",
        )
