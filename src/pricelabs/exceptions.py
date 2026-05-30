"""Exception hierarchy for the PriceLabs Python SDK."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

logger = logging.getLogger(__name__)


class PriceLabsError(Exception):
    """Base exception for all PriceLabs SDK errors."""


class APIError(PriceLabsError):
    """Raised when the PriceLabs API returns an error response."""

    def __init__(self, message: str, status_code: int, raw: dict | None = None) -> None:
        """Initialize APIError with message, HTTP status code, and optional raw response body.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code from the response.
            raw: Parsed JSON body of the error response, if available.
        """
        super().__init__(message)
        self.status_code = status_code
        self.raw = raw


class AuthenticationError(APIError):
    """Raised when the API returns 401 Unauthorized."""


class ForbiddenError(APIError):
    """Raised when the API returns 403 Forbidden."""


class NotFoundError(APIError):
    """Raised when the API returns 404 Not Found."""


class InvalidRequestError(APIError):
    """Raised when the API returns 422 Unprocessable Entity."""


class RateLimitError(APIError):
    """Raised when the API returns 429 Too Many Requests."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        raw: dict | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Initialize RateLimitError with an optional retry delay.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code (default 429).
            raw: Parsed JSON body of the error response, if available.
            retry_after: Seconds to wait before retrying, from the Retry-After header.
        """
        super().__init__(message, status_code, raw)
        self.retry_after = retry_after


class ServerError(APIError):
    """Raised when the API returns a 5xx server error."""


class ConfigurationError(PriceLabsError):
    """Raised for SDK configuration problems such as a missing API key."""


class NetworkError(PriceLabsError):
    """Raised when a network-level failure prevents the request from completing."""


def raise_for_status(response: "httpx.Response") -> None:
    """Raise the appropriate exception for a non-2xx HTTP response.

    Parses the response body as JSON to extract an error message. Falls back to
    the HTTP status code as the message if the body is not valid JSON or is empty.

    Does nothing for 2xx responses.

    Args:
        response: The httpx.Response to inspect.

    Raises:
        AuthenticationError: For 401 responses.
        ForbiddenError: For 403 responses.
        NotFoundError: For 404 responses.
        InvalidRequestError: For 422 responses.
        RateLimitError: For 429 responses.
        ServerError: For 5xx responses.
        APIError: For other 4xx responses.
    """
    status = response.status_code

    if status < 400:
        return

    raw: dict | None = None
    try:
        raw = response.json()
        message: str = raw.get("message") or raw.get("error") or str(status)
    except Exception:
        message = str(status)

    logger.warning("API error response: status=%d message=%s", status, message)

    if status == 401:
        raise AuthenticationError(message, status, raw)
    if status == 403:
        raise ForbiddenError(message, status, raw)
    if status == 404:
        raise NotFoundError(message, status, raw)
    if status == 422:
        raise InvalidRequestError(message, status, raw)
    if status == 429:
        retry_after: int | None = None
        retry_after_header = response.headers.get("Retry-After")
        if retry_after_header is not None:
            try:
                retry_after = int(retry_after_header)
            except ValueError:
                logger.warning("Could not parse Retry-After header: %r", retry_after_header)
        raise RateLimitError(message, status, raw, retry_after)
    if 500 <= status <= 599:
        raise ServerError(message, status, raw)

    raise APIError(message, status, raw)
