import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import List

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import DatabaseManager, check_db_connection
from src.domain.service import CommitService
from src.utils import SingletonHttpx
from src.webapp.dependencies import get_commit_service
from src.webapp.schemas import (
    AuthorCommitsListResponse,
    AuthorCommitStatsResponse,
    CommitDetailResponse,
    StatusResponse,
)
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


app = FastAPI(
    title="Commit Tracker API",
    description="API to fetch and display commits from a public developer platform, such as GitHub.",
    version="1.0.0",
    lifespan=life_span,
)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    responses={500: {"description": "Internal server error"}},
)
async def health_check(
    session: AsyncSession = Depends(DatabaseManager.get_session),
) -> StatusResponse:
    """
    Endpoint that checks if the app and database are functioning.

    Args:
        session (AsyncSession): The database session.

    Returns:
        - HTTP 200:: `OK` status for the application and database.
        - HTTP 500: If something goes wrong.
    """

    db_connection_status = await check_db_connection(session)

    if not db_connection_status:
        _logger.warning("Health check failed due to unhealty Database!")
        raise HTTPException(status_code=500, detail="Database connection failed")

    return StatusResponse(status="OK")


@app.post(
    "/commits/trigger-fetch",
    status_code=status.HTTP_200_OK,
    responses={500: {"description": "Internal server error"}},
)
async def trigger_commit_fetch(
    background_tasks: BackgroundTasks,
    httpx_client: httpx.AsyncClient = Depends(SingletonHttpx.get_httpx_client),
    settings: Settings = Depends(get_settings),
    commit_service: CommitService = Depends(get_commit_service),
) -> StatusResponse:
    """
    Triggers a background task to fetch and stores the latest 1000 commits.
    Returns immediately while processing continues in background.

    Returns:
        - HTTP 200: Background task is successfully triggered.
        - HTTP 500: An internal error occured.
    """
    try:
        # Ideally, this background task should be offloaded to a task queue like Celery.
        background_tasks.add_task(
            commit_service.retrieve_and_store_commits,
            httpx_client=httpx_client,
            token=settings.GITHUB_ACCESS_TOKEN,
        )
        _logger.info("Background task for commits fetch is successfully scheduled.")
        return StatusResponse(status="Processing started in background")
    except Exception as ex:
        _logger.error(
            f"Failed to schedule background task. Exception: {ex}",
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
        404: {"description": "Commits not found for the author"},
        500: {"description": "Internal server error"},
    },
)
async def get_commits_by_author(
    author_identifier: str,
    commit_service=Depends(get_commit_service),
) -> List[CommitDetailResponse]:
    """
    Retrieves a list of commits for a given author based on their name or email.

    Returns:
        - HTTP 200: A list of commits for the given author.
        - HTTP 404: If no commits are found for the author.
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
            f"Error while retrieving commits for: '{author_identifier}'. Exception: {ex}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong",
        )

    if not commits:
        _logger.info(f"No commits found for: '{author_identifier}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No commits found for: {author_identifier}",
        )

    return commits


@app.get(
    "/commits/authors/summary",
    status_code=status.HTTP_200_OK,
    responses={500: {"description": "Internal server error"}},
)
async def get_aggregated_commits_data_by_author(
    commit_service=Depends(get_commit_service),
) -> List[AuthorCommitStatsResponse]:
    """
    Retrieves aggregated commit data grouped by author.

    This endpoint fetches the total number of commits and the latest commit date
    for each author in the database.

    Returns:
        - HTTP 200: A list of authors with their aggregated commit data.
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
    responses={500: {"description": "Internal server error"}},
)
async def get_commits_list_grouped_by_author_for_last_week(
    commit_service=Depends(get_commit_service),
) -> List[AuthorCommitsListResponse]:
    """
    Retrieves a list of commits grouped by authors for the last 7 days.

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
