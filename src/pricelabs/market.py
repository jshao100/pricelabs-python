"""Pydantic models and namespace for the PriceLabs neighborhood/market data API."""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pricelabs._http import HTTPClient

logger = logging.getLogger(__name__)


class BedroomCategory(BaseModel):
    """Price or occupancy data for a single bedroom count category."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    x_values: list[str] | None = Field(None, alias="X_values")
    y_values: Any = Field(None, alias="Y_values")
    listings_used: int | None = Field(None, alias="Listings Used")
    active_used: int | None = Field(None, alias="Active Used")
    inactive_used: int | None = Field(None, alias="Inactive Used")


class DataSection(BaseModel):
    """A section of neighborhood data with bedroom categories and labels.

    The API returns sections like "Future Percentile Prices" with a "Category"
    dict keyed by bedroom count ("-1", "0", "1", etc.) and a "Labels" list.
    """

    category: dict[str, BedroomCategory] = Field(default_factory=dict, alias="Category")
    labels: list[str] = Field(default_factory=list, alias="Labels")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NeighborhoodData(BaseModel):
    """Top-level model for the GET /v1/neighborhood_data API response."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    listings_used: int = Field(alias="Listings Used")
    currency: str
    lat: float
    lng: float
    source: str
    neighborhood_data_source: str = Field(alias="Neighborhood Data Source")
    future_percentile_prices: DataSection = Field(alias="Future Percentile Prices")
    summary_table_base_price: DataSection = Field(alias="Summary Table Base Price")
    future_occupancy: DataSection = Field(alias="Future Occ/New/Canc")
    market_kpi: DataSection | None = Field(None, alias="Market KPI")


class Market:
    """Resource namespace for neighborhood/market data."""

    def __init__(self, http: HTTPClient) -> None:
        """Initialise the Market namespace with an HTTP client.

        Args:
            http: Configured HTTP transport client.
        """
        self._http = http

    def neighborhood(self, listing_id: str, pms: str) -> NeighborhoodData:
        """Fetch neighborhood data for a listing.

        Args:
            listing_id: PriceLabs listing identifier.
            pms: Property management system identifier (e.g. ``"airbnb"``).

        Returns:
            Parsed ``NeighborhoodData`` for the listing.
        """
        logger.info("Fetching neighborhood data listing_id=%s pms=%s", listing_id, pms)
        data = self._http.get(
            "/v1/neighborhood_data",
            params={"pms": pms, "listing_id": listing_id},
        )
        result = NeighborhoodData.model_validate(data["data"])
        logger.info("Fetched neighborhood data listing_id=%s", listing_id)
        return result
