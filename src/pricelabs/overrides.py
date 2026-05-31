"""Date-specific override (DSO) resource namespace."""

import logging
from typing import Any

from pydantic import BaseModel, field_validator

from pricelabs._http import HTTPClient

logger = logging.getLogger(__name__)


class DateSpecificOverride(BaseModel):
    """A date-specific pricing override returned by the PriceLabs API.

    Attributes:
        date: Calendar date in YYYY-MM-DD format.
        created_at: ISO 8601 creation timestamp.
        updated_at: ISO 8601 last-modified timestamp.
        price: Override price value (string representation).
        price_type: How price is applied — ``fixed`` or ``percent``.
        currency: ISO 4217 currency code.
        min_stay: Minimum stay in nights.
        min_price: Minimum price floor.
        min_price_type: How min_price is applied — ``fixed``, ``percent_base``, or ``percent_min``.
        max_price: Maximum price ceiling.
        max_price_type: How max_price is applied — ``fixed``, ``percent_base``, or ``percent_max``.
        base_price: Base price used as reference for percent calculations.
        check_in_check_out_enabled: Whether check-in/out restrictions are active
            (``"0"`` or ``"1"``).
        check_in: 7-char binary string Mon–Sun indicating allowed check-in days.
        check_out: 7-char binary string Mon–Sun indicating allowed check-out days.
        reason: Human-readable note describing why this override exists.
    """

    date: str
    created_at: str | None = None
    updated_at: str | None = None
    price: str | None = None
    price_type: str | None = None
    currency: str | None = None
    min_stay: int | None = None
    min_price: float | None = None
    min_price_type: str | None = None
    max_price: float | None = None
    max_price_type: str | None = None
    base_price: float | None = None
    check_in_check_out_enabled: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    reason: str | None = None

    @field_validator("min_price", "max_price", "base_price", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> Any:
        """Coerce numeric string values returned by the API to float."""
        if isinstance(v, str):
            return float(v)
        return v


class OverrideInput(BaseModel):
    """Input model for creating or updating a date-specific override.

    Attributes:
        date: Calendar date in YYYY-MM-DD format (required).
        price: Price value to apply.
        price_type: How price is applied — ``fixed`` or ``percent``.
        min_stay: Minimum stay in nights.
        min_price: Minimum price floor.
        min_price_type: How min_price is applied.
        max_price: Maximum price ceiling.
        max_price_type: How max_price is applied.
        check_in_check_out_enabled: Enable check-in/out restrictions (``"0"`` or ``"1"``).
        check_in: 7-char binary string Mon–Sun for allowed check-in days.
        check_out: 7-char binary string Mon–Sun for allowed check-out days.
        reason: Human-readable note for this override.
    """

    date: str
    price: str | None = None
    price_type: str | None = None
    min_stay: int | None = None
    min_price: float | None = None
    min_price_type: str | None = None
    max_price: float | None = None
    max_price_type: str | None = None
    check_in_check_out_enabled: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    reason: str | None = None


class Overrides:
    """Resource namespace for date-specific overrides (DSO).

    Args:
        http: Configured HTTP transport client.
    """

    def __init__(self, http: HTTPClient) -> None:
        """Initialise the Overrides namespace with an HTTP client."""
        self._http = http

    def list(self, listing_id: str, pms: str) -> list[DateSpecificOverride]:
        """Retrieve all date-specific overrides for a listing.

        Args:
            listing_id: PriceLabs listing identifier.
            pms: Property management system identifier (e.g. ``"airbnb"``).

        Returns:
            List of ``DateSpecificOverride`` objects.
        """
        path = f"/v1/listings/{listing_id}/overrides"
        logger.info("Fetching overrides listing_id=%s pms=%s", listing_id, pms)
        data = self._http.get(path, params={"pms": pms})
        overrides = [
            DateSpecificOverride.model_validate(item) for item in data.get("overrides", [])
        ]
        logger.info("Fetched %d overrides listing_id=%s", len(overrides), listing_id)
        return overrides

    def create(
        self,
        listing_id: str,
        pms: str,
        overrides: list[OverrideInput],
        update_children: bool = False,
    ) -> list[DateSpecificOverride]:
        """Create or update date-specific overrides for a listing.

        Args:
            listing_id: PriceLabs listing identifier.
            pms: Property management system identifier.
            overrides: List of overrides to create or update.
            update_children: When True, propagate changes to child listings.

        Returns:
            List of created or updated ``DateSpecificOverride`` objects.
        """
        path = f"/v1/listings/{listing_id}/overrides"
        body = {
            "pms": pms,
            "update_children": update_children,
            "overrides": [o.model_dump(exclude_none=True) for o in overrides],
        }
        logger.info(
            "Creating %d overrides listing_id=%s pms=%s update_children=%s",
            len(overrides),
            listing_id,
            pms,
            update_children,
        )
        data = self._http.post(path, json=body, retryable=True)
        created = [DateSpecificOverride.model_validate(item) for item in data.get("overrides", [])]
        logger.info("Created %d overrides listing_id=%s", len(created), listing_id)
        return created

    def delete(
        self,
        listing_id: str,
        pms: str,
        dates: list[str],
        update_children: bool = False,
    ) -> None:
        """Delete date-specific overrides for a listing.

        Args:
            listing_id: PriceLabs listing identifier.
            pms: Property management system identifier.
            dates: List of calendar dates (YYYY-MM-DD) to remove overrides for.
            update_children: When True, propagate deletions to child listings.
        """
        path = f"/v1/listings/{listing_id}/overrides"
        body = {
            "pms": pms,
            "update_children": update_children,
            "overrides": [{"date": d} for d in dates],
        }
        logger.info(
            "Deleting %d overrides listing_id=%s pms=%s update_children=%s",
            len(dates),
            listing_id,
            pms,
            update_children,
        )
        self._http.delete(path, json=body)
        logger.info("Deleted overrides listing_id=%s dates=%s", listing_id, dates)
