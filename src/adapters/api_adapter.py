"""
API Adapter for storing and retrieving commits from an external API.

This module provides an adapter that extends the base `CommitStorage` class,
intended for use with an external API. The current implementation serves as a
placeholder, allowing for future integration with an actual API without modifying
the core application logic.

This design allows for flexibility in case the storage solution needs to switch
from a database (such as the one used in the `DatabaseStorage`) to an
external API, without requiring major changes to the overall system.
"""

from src.adapters.storage import CommitStorage


class ExternalAPIStorage(CommitStorage):
    pass
