import logging
from typing import Optional

import httpx

_logger = logging.getLogger(__name__)


class SingletonHttpx:
    """
    A singleton class for managing a single instance of `httpx.AsyncClient`.

    This class ensures that only one instance of `httpx.AsyncClient` is created and used
    throughout the application.
    """

    httpx_client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_httpx_client(cls) -> httpx.AsyncClient:
        """
        Retrieves an instance of `httpx.AsyncClient`.

        Returns:
            httpx.AsyncClient: The singleton `httpx.AsyncClient` instance.
        """
        if cls.httpx_client is None:
            _logger.info("Initializing new httpx.AsyncClient instance")

            client_timeout = 10
            cls.httpx_client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout=client_timeout)
            )

            _logger.info(
                f"HTTPX client initialized with timeout = {client_timeout} seconds."
            )
        return cls.httpx_client

    @classmethod
    async def close_httpx_client(cls) -> None:
        """
        Closes the `httpx.AsyncClient` instance.
        """
        if cls.httpx_client:
            _logger.info("Closing HTTPX client..")
            await cls.httpx_client.aclose()
            cls.httpx_client = None
