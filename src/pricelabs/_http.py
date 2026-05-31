"""HTTP transport layer for the PriceLabs Python SDK."""

import logging
import time
from typing import Any

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
from tenacity.wait import wait_base

from pricelabs._version import __version__
from pricelabs.exceptions import raise_for_status

logger = logging.getLogger(__name__)

_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})


class _RetryableHTTPError(Exception):
    """Raised for HTTP status codes that should be retried."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"HTTP {response.status_code}")


class _RetryAfterWait(wait_base):
    """Wait strategy that respects the Retry-After response header.

    Falls back to exponential jitter when the header is absent, and uses
    ``max(retry_after, jitter)`` when it is present.
    """

    def __init__(self, fallback: wait_base) -> None:
        self._fallback = fallback

    def __call__(self, retry_state: Any) -> float:
        """Compute wait duration for the next retry attempt."""
        exc = retry_state.outcome.exception()
        if isinstance(exc, _RetryableHTTPError):
            raw = exc.response.headers.get("Retry-After")
            if raw is not None:
                try:
                    return max(float(raw), self._fallback(retry_state))
                except (ValueError, TypeError):
                    pass
        return self._fallback(retry_state)


class HTTPClient:
    """HTTP transport client for the PriceLabs Customer API.

    Args:
        base_url: Base URL for all requests (e.g. ``https://api.pricelabs.co``).
        api_key: PriceLabs API key sent as ``X-API-Key`` header.
        timeout: Per-request timeout in seconds. Defaults to 300.
        max_retries: Maximum total attempts (including the first). Defaults to 5.
        _sleep_fn: Override the sleep callable used by the retry loop (testing only).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 300,
        max_retries: int = 5,
        _sleep_fn: Any = None,
    ) -> None:
        self.max_retries = max_retries
        self._sleep_fn: Any = _sleep_fn if _sleep_fn is not None else time.sleep
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "X-API-Key": api_key,
                "User-Agent": f"pricelabs-python/{__version__}",
            },
        )
        logger.info("HTTPClient initialized base_url=%s", base_url)

    def _request(
        self,
        method: str,
        path: str,
        retryable: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request, retrying on transient failures when enabled.

        Args:
            method: HTTP verb (GET, POST, DELETE, …).
            path: Path relative to base_url.
            retryable: When True, retry on 429/502/503/504 and network errors.
            **kwargs: Additional arguments forwarded to ``httpx.Client.request``.

        Returns:
            The successful HTTP response.

        Raises:
            Exception: After all retries are exhausted or for non-retryable errors.
        """

        def _attempt() -> httpx.Response:
            logger.debug("%s %s", method, path)
            response = self._client.request(method, path, **kwargs)
            if retryable and response.status_code in _RETRYABLE_STATUSES:
                logger.warning(
                    "Retryable status %d on %s %s", response.status_code, method, path
                )
                raise _RetryableHTTPError(response)
            raise_for_status(response)
            return response

        retrying = Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=_RetryAfterWait(wait_exponential_jitter(initial=1, max=60)),
            retry=retry_if_exception_type(
                (_RetryableHTTPError, httpx.ConnectError, httpx.TimeoutException)
            ),
            sleep=self._sleep_fn,
            reraise=True,
        )

        try:
            return retrying(_attempt)
        except _RetryableHTTPError as exc:
            logger.error(
                "Request failed after %d attempts: %s %s", self.max_retries, method, path
            )
            raise_for_status(exc.response)
            raise  # pragma: no cover  # unreachable; raise_for_status always raises for 4xx/5xx

    def get(self, path: str, params: dict | None = None) -> dict:
        """Send a GET request and return the parsed JSON body.

        Args:
            path: Request path.
            params: Optional URL query parameters.

        Returns:
            Parsed JSON response as a dict.
        """
        response = self._request("GET", path, retryable=True, params=params)
        return response.json()

    def post(self, path: str, json: dict | None = None, retryable: bool = False) -> dict:
        """Send a POST request and return the parsed JSON body.

        Args:
            path: Request path.
            json: Optional JSON request body.
            retryable: When True, retry on transient server errors.

        Returns:
            Parsed JSON response as a dict.
        """
        response = self._request("POST", path, retryable=retryable, json=json)
        return response.json()

    def delete(self, path: str, json: dict | None = None) -> dict | None:
        """Send a DELETE request and return the parsed JSON body or None for 204.

        Args:
            path: Request path.
            json: Optional JSON request body.

        Returns:
            Parsed JSON response as a dict, or None when the server returns 204.
        """
        response = self._request("DELETE", path, retryable=True, json=json)
        if response.status_code == 204:
            return None
        return response.json()

    def close(self) -> None:
        """Close the underlying httpx client and release connections."""
        self._client.close()
        logger.info("HTTPClient closed")
