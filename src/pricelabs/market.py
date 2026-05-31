"""Pydantic models for the PriceLabs neighborhood/market data API response."""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)


class BedroomCategory(BaseModel):
    """Price or occupancy data for a single bedroom count category."""

    x_values: list[str] = Field(alias="X_values")
    y_values: list[list[float]] = Field(alias="Y_values")
    listings_used: int | None = Field(None, alias="Listings Used")
    active_used: int | None = Field(None, alias="Active Used")
    inactive_used: int | None = Field(None, alias="Inactive Used")

    model_config = ConfigDict(populate_by_name=True)


class DataSection(BaseModel):
    """A section of neighborhood data with bedroom categories and labels.

    The API returns bedroom count keys ("-1", "0", "1", "2", ...) as siblings
    of "Labels" in a flat dict.  The model_validator separates them into a
    ``category`` dict and a ``labels`` list.
    """

    category: dict[str, BedroomCategory] = Field(default_factory=dict)
    labels: list[str] = Field(alias="Labels")

    _RESERVED_KEYS: ClassVar[set[str]] = {"Labels"}

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _extract_categories(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        categories: dict[str, Any] = {}
        remaining: dict[str, Any] = {}
        for key, value in data.items():
            if key not in cls._RESERVED_KEYS and isinstance(value, dict):
                categories[key] = value
            else:
                remaining[key] = value
        remaining["category"] = categories
        logger.debug("Extracted %d bedroom categories", len(categories))
        return remaining


class OccupancyData(BaseModel):
    """Occupancy, new bookings, and cancellation trend data."""

    x_values: list[str] = Field(alias="X_values")
    y_values: list[list[float]] = Field(alias="Y_values")
    labels: list[str] = Field(alias="Labels")

    model_config = ConfigDict(populate_by_name=True)


class MarketKPI(BaseModel):
    """Market-level key performance indicators."""

    avg_daily_rate: float
    revenue_per_available_night: float
    occupancy_rate: float
    avg_booking_lead_time_days: int
    avg_length_of_stay_days: float
    total_active_listings: int

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NeighborhoodData(BaseModel):
    """Top-level model for the GET /v1/neighborhood_data API response."""

    listings_used: int = Field(alias="Listings Used")
    currency: str
    lat: float
    lng: float
    source: str
    neighborhood_data_source: str = Field(alias="Neighborhood Data Source")
    future_percentile_prices: DataSection = Field(alias="Future Percentile Prices")
    summary_table_base_price: DataSection = Field(alias="Summary Table Base Price")
    future_occupancy: OccupancyData = Field(alias="Future Occ/New/Canc")
    market_kpi: MarketKPI | None = Field(None, alias="Market KPI")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
