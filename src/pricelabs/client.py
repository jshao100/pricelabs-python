"""Top-level PriceLabs client."""

import logging
import os

from pricelabs._http import HTTPClient
from pricelabs.exceptions import ConfigurationError
from pricelabs.listings import Listings
from pricelabs.market import Market
from pricelabs.overrides import Overrides
from pricelabs.prices import Prices
from pricelabs.reservations import Reservations

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.pricelabs.co"


class PriceLabsClient:
    """Client for the PriceLabs Customer API.

    Args:
        api_key: PriceLabs API key. Falls back to the ``PRICELABS_API_KEY`` env var.
        base_url: API base URL. Falls back to ``PRICELABS_BASE_URL`` env var or the
            production default.
        timeout: Per-request timeout in seconds. Defaults to 300.
        max_retries: Maximum total attempts (including the first). Defaults to 5.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 300,
        max_retries: int = 5,
    ) -> None:
        resolved_key = api_key or os.environ.get("PRICELABS_API_KEY", "")
        if not resolved_key:
            raise ConfigurationError(
                "api_key is required. Pass it explicitly or set PRICELABS_API_KEY."
            )

        resolved_url = base_url or os.environ.get("PRICELABS_BASE_URL", _DEFAULT_BASE_URL)

        self._http = HTTPClient(
            base_url=resolved_url,
            api_key=resolved_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._overrides = Overrides(self._http)
        self._market = Market(self._http)
        self._reservations = Reservations(self._http)
        logger.info("PriceLabsClient initialized base_url=%s", resolved_url)

    @property
    def listings(self) -> Listings:
        """Return the Listings resource namespace (lazily initialized)."""
        if not hasattr(self, "_listings"):
            self._listings = Listings(self._http)
        return self._listings

    @property
    def overrides(self) -> Overrides:
        """Namespace for date-specific override (DSO) operations."""
        return self._overrides

    @property
    def market(self) -> Market:
        """Namespace for neighborhood/market data operations."""
        return self._market

    @property
    def prices(self) -> Prices:
        """Access the Prices resource namespace."""
        return Prices(self._http)

    @property
    def reservations(self) -> Reservations:
        """Namespace for reservation-related API operations."""
        return self._reservations

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._http.close()
        logger.info("PriceLabsClient closed")
