class GitProviderDataValidationError(Exception):
    """
    Raised when raw data received from the Git provider fails validation.

    This exception indicates that the data retrieved from the Git provider
    does not meet the expected format or contains errors, preventing further processing.
    """

    pass
