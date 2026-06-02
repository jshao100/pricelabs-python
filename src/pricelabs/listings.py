"""Listings resource namespace for the PriceLabs Python SDK."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pricelabs._http import HTTPClient

logger = logging.getLogger(__name__)


class ChannelDetail(BaseModel):
    """A channel-specific listing identifier and URL."""

    model_config = ConfigDict(populate_by_name=True)

    channel_name: str = Field(alias="channel")
    channel_listing_id: str = Field(alias="listing_id")
    listing_url: str | None = None


class Listing(BaseModel):
    """A PriceLabs listing with pricing, occupancy, and metadata."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    pms: str
    name: str | None = None
    latitude: float | None = Field(None, alias="lat")
    longitude: float | None = Field(None, alias="lng")
    country: str | None = None
    city_name: str | None = None
    state: str | None = None
    no_of_bedrooms: int | None = None
    channel_listing_details: list[ChannelDetail] = Field(default_factory=list)
    min: float | None = None
    base: float | None = None
    max: float | None = None
    group: str | None = None
    subgroup: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    isHidden: bool = False
    push_enabled: bool = False
    occupancy_next_7: float | None = None
    occupancy_next_30: float | None = None
    occupancy_next_60: float | None = None
    occupancy_next_90: float | None = None
    market_occupancy_next_7: float | None = None
    market_occupancy_next_30: float | None = None
    market_occupancy_next_60: float | None = None
    market_occupancy_next_90: float | None = None
    revenue_past_7: float | None = None
    stly_revenue_past_7: float | None = None
    recommended_base_price: str | None = None
    last_date_pushed: str | None = None
    last_refreshed_at: str | None = None

    @field_validator(
        "occupancy_next_7", "occupancy_next_30", "occupancy_next_60", "occupancy_next_90",
        "market_occupancy_next_7", "market_occupancy_next_30", "market_occupancy_next_60",
        "market_occupancy_next_90",
        mode="before",
    )
    @classmethod
    def coerce_percent_string(cls, v: Any) -> float | None:
        """Strip '%' suffix from percentage strings like '43 %'."""
        if v is None:
            return None
        if isinstance(v, str):
            return float(v.replace("%", "").strip())
        return v

    @field_validator("recommended_base_price", mode="before")
    @classmethod
    def coerce_recommended_base_price(cls, v: Any) -> str | None:
        """Coerce numeric recommended_base_price values to str."""
        if v is None:
            return None
        return str(v)


class ListingUpdate(BaseModel):
    """Input model for updating a listing's pricing parameters."""

    id: str
    pms: str
    min: float | None = None
    base: float | None = None
    max: float | None = None
    tags: list[str] | None = None


class Listings:
    """Namespace for the /v1/listings API endpoints."""

    def __init__(self, http: HTTPClient) -> None:
        """Initialize with an HTTPClient instance.

        Args:
            http: The HTTP client to use for requests.
        """
        self._http = http

    def list(self, skip_hidden: bool = False, only_syncing: bool = False) -> list[Listing]:
        """Fetch all listings for the account.

        Args:
            skip_hidden: When True, exclude hidden listings from results.
            only_syncing: When True, return only listings actively syncing prices.

        Returns:
            List of Listing objects.
        """
        params = {
            "skip_hidden": "true" if skip_hidden else "false",
            "only_syncing_listings": "true" if only_syncing else "false",
        }
        logger.info(
            "Fetching listings skip_hidden=%s only_syncing=%s", skip_hidden, only_syncing
        )
        data = self._http.get("/v1/listings", params=params)
        listings = [Listing.model_validate(item) for item in data["listings"]]
        logger.info("Fetched %d listings", len(listings))
        return listings

    def get(self, listing_id: str) -> Listing:
        """Fetch a single listing by ID.

        Args:
            listing_id: The listing's unique ID.

        Returns:
            The matching Listing object.
        """
        logger.info("Fetching listing id=%s", listing_id)
        data = self._http.get(f"/v1/listings/{listing_id}")
        items = data.get("listings", [data])
        listing = Listing.model_validate(items[0])
        logger.info("Fetched listing id=%s", listing_id)
        return listing

    def update(self, listings: list[ListingUpdate]) -> list[dict]:
        """Update pricing parameters for one or more listings.

        Args:
            listings: List of ListingUpdate objects with new pricing data.

        Returns:
            List of dicts with the API response for each updated listing.
        """
        body = {"listings": [u.model_dump(exclude_none=True) for u in listings]}
        logger.info("Updating %d listings", len(listings))
        data = self._http.post("/v1/listings", json=body, retryable=True)
        updated: list[dict] = data.get("listings", [])
        logger.info("Updated %d listings", len(updated))
        return updated

    def import_from_pms(self, listing_id: str, pms_name: str) -> dict:
        """Import a listing from a PMS into PriceLabs.

        Args:
            listing_id: The listing's unique ID.
            pms_name: The PMS name to import from (e.g. "airbnb").

        Returns:
            API response as a dict.
        """
        body: dict[str, str] = {"listing_id": listing_id, "pms_name": pms_name}
        logger.info("Importing listing id=%s from pms=%s", listing_id, pms_name)
        data = self._http.post("/v1/add_listing_data", json=body, retryable=False)
        logger.info("Imported listing id=%s", listing_id)
        return data
