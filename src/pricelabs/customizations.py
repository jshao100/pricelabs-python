"""Listing customizations resource namespace."""

import logging

from pydantic import BaseModel

from pricelabs._http import HTTPClient

logger = logging.getLogger(__name__)


class LastMinutePrices(BaseModel):
    """Last-minute pricing discount settings.

    Attributes:
        last_min_factor_on: Enable/disable last-minute discounts.
        last_min_factor_type: One of ``none``, ``recommended``,
            ``conservative``, ``aggressive``, ``linear``,
            ``linear_gradual``, ``fixed``.
        last_min_factor_value: Discount value for linear/linear_gradual/fixed.
        last_min_factor_dfd: Days from date (1-90).
    """

    last_min_factor_on: bool | None = None
    last_min_factor_type: str | None = None
    last_min_factor_value: float | None = None
    last_min_factor_dfd: int | None = None


class Seasonality(BaseModel):
    """Seasonality adjustment settings.

    Attributes:
        seasonality_customization_on: Enable/disable seasonality block.
        seasonality_type: One of ``no_seasonality``, ``conservative``,
            ``moderately_conservative``, ``recommended``,
            ``moderately_aggressive``, ``aggressive``.
    """

    seasonality_customization_on: bool | None = None
    seasonality_type: str | None = None


class DayOfWeekAdjustment(BaseModel):
    """Day-of-week price adjustment settings.

    Attributes:
        dow_factor_on: Enable/disable day-of-week adjustments.
        dow_factor_value_mon: Monday adjustment (-75..1000).
        dow_factor_value_tue: Tuesday adjustment (-75..1000).
        dow_factor_value_wed: Wednesday adjustment (-75..1000).
        dow_factor_value_thu: Thursday adjustment (-75..1000).
        dow_factor_value_fri: Friday adjustment (-75..1000).
        dow_factor_value_sat: Saturday adjustment (-75..1000).
        dow_factor_value_sun: Sunday adjustment (-75..1000).
    """

    dow_factor_on: bool | None = None
    dow_factor_value_mon: int | None = None
    dow_factor_value_tue: int | None = None
    dow_factor_value_wed: int | None = None
    dow_factor_value_thu: int | None = None
    dow_factor_value_fri: int | None = None
    dow_factor_value_sat: int | None = None
    dow_factor_value_sun: int | None = None


class FarOutPremium(BaseModel):
    """Far-out premium pricing settings.

    Attributes:
        far_out_premium_on: Enable/disable far-out premium.
        far_out_premium_type: One of ``none``, ``recommended``,
            ``conservative``, ``aggressive``, ``linear``, ``fix``
            (note: ``fix``, not ``fixed``).
        far_out_premium_value: Premium value.
        far_out_premium_start: Start day (1-999).
        far_out_premium_step: Step size (1-999).
    """

    far_out_premium_on: bool | None = None
    far_out_premium_type: str | None = None
    far_out_premium_value: int | None = None
    far_out_premium_start: int | None = None
    far_out_premium_step: int | None = None


class DemandFactor(BaseModel):
    """Demand factor and hotel comp-set settings.

    Attributes:
        tone_demand_factor_on: Enable/disable demand factor.
        tone_demand_factor: One of ``conservative``,
            ``moderately_conservative``, ``recommended``,
            ``moderately_aggressive``, ``aggressive``,
            ``no demand factor`` (note the spaces).
        hotel_compset_type: One of ``recommended``, ``custom``
            (feature-gated).
        hotel_wt: One of ``fully_str``, ``mostly_str``, ``balance``,
            ``mostly_hotel``, ``fully_hotel`` (feature-gated).
    """

    tone_demand_factor_on: bool | None = None
    tone_demand_factor: str | None = None
    hotel_compset_type: str | None = None
    hotel_wt: str | None = None


class ListingCustomizations(BaseModel):
    """Nested customizations container for a single listing.

    Contains 5 optional sub-objects matching the PriceLabs
    CapiCustomizationsMap schema. An empty API response produces
    an all-None instance.

    Attributes:
        last_minute_prices: Last-minute discount settings.
        seasonality: Seasonality adjustment settings.
        day_of_week_adjustment: Day-of-week price adjustments.
        far_out_premium: Far-out premium settings.
        demand_factor: Demand factor and hotel comp-set settings.
    """

    last_minute_prices: LastMinutePrices | None = None
    seasonality: Seasonality | None = None
    day_of_week_adjustment: DayOfWeekAdjustment | None = None
    far_out_premium: FarOutPremium | None = None
    demand_factor: DemandFactor | None = None


class Customizations:
    """Resource namespace for listing customizations.

    Args:
        http: Configured HTTP transport client.
    """

    def __init__(self, http: HTTPClient) -> None:
        """Initialise the Customizations namespace with an HTTP client."""
        self._http = http

    def get(
        self,
        listing_id: str,
        pms: str,
        customizations: str | None = None,
        toggled_on: bool = True,
    ) -> ListingCustomizations:
        """Retrieve customizations for a listing.

        Args:
            listing_id: PriceLabs listing identifier.
            pms: Property management system identifier.
            customizations: Optional comma-separated filter of customization
                keys to return.
            toggled_on: When True (default), return only enabled blocks.

        Returns:
            A ``ListingCustomizations`` instance (all-None when the listing
            uses defaults).
        """
        path = "/v1/customizations/listing"
        params: dict = {
            "listing_id": listing_id,
            "pms_name": pms,
            "toggled_on": toggled_on,
        }
        if customizations is not None:
            params["customizations"] = customizations
        logger.info("Fetching customizations listing_id=%s pms=%s", listing_id, pms)
        data = self._http.get(path, params=params)
        raw = data.get("customizations") or {}
        result = ListingCustomizations.model_validate(raw)
        logger.info("Fetched customizations listing_id=%s", listing_id)
        return result

    def update(
        self,
        listing_id: str,
        pms: str,
        customizations: ListingCustomizations,
    ) -> dict:
        """Update customizations for a listing.

        Args:
            listing_id: PriceLabs listing identifier.
            pms: Property management system identifier.
            customizations: Customization fields to set. Only non-None fields
                are sent.

        Returns:
            Raw API response dict.
        """
        path = "/v1/customizations/listing"
        body = {
            "listing_id": listing_id,
            "pms_name": pms,
            "customizations": customizations.model_dump(exclude_none=True),
        }
        logger.info("Updating customizations listing_id=%s pms=%s", listing_id, pms)
        result = self._http.post(path, json=body)
        logger.info("Updated customizations listing_id=%s", listing_id)
        return result
