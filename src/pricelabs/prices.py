"""Prices resource namespace for the PriceLabs API."""

import logging
from typing import Any, cast

from pydantic import BaseModel, ConfigDict

from pricelabs._http import HTTPClient

logger = logging.getLogger(__name__)

_ERROR_STATUSES = frozenset({"LISTING_NOT_PRESENT", "LISTING_NO_DATA", "LISTING_TOGGLE_OFF"})


class PriceRequest(BaseModel):
    """Input model for requesting prices for a listing.

    Attributes:
        id: Listing ID.
        pms: PMS name (e.g. ``airbnb``, ``ownerrez``).
        date_from: Start date in ``YYYY-MM-DD`` format; defaults to today when omitted.
        date_to: End date in ``YYYY-MM-DD`` format; defaults to a rolling window when omitted.
        reason: When True, the API includes pricing reason data in the response.
    """

    id: str
    pms: str
    date_from: str | None = None
    date_to: str | None = None
    reason: bool = False


class LOSPricing(BaseModel):
    """Length-of-stay pricing adjustment for a given night count.

    Attributes:
        los_night: Number of nights this entry applies to.
        max_price: Maximum price cap for this LOS tier.
        min_price: Minimum price floor for this LOS tier.
        los_adjustment: Fractional price adjustment (e.g. ``-0.10`` for a 10% discount).
    """

    los_night: int
    max_price: float
    min_price: float
    los_adjustment: float


class MarketFactors(BaseModel):
    """Market-level pricing signals for a given day.

    Attributes:
        local_events: Events influencing demand on this date.
        seasonality_score: Seasonality adjustment factor (0–1).
        day_of_week_multiplier: Price multiplier based on day of week.
        lead_time_days: Days between today and the stay date.
        supply_demand_ratio: Ratio of supply to demand (>1 means oversupply).
    """

    model_config = ConfigDict(extra="allow")

    local_events: list[str] | None = None
    seasonality_score: float | None = None
    day_of_week_multiplier: float | None = None
    lead_time_days: int | None = None
    supply_demand_ratio: float | None = None


class PricingCustomizations(BaseModel):
    """User-applied pricing customizations active on a given day.

    Attributes:
        user_override: Whether a manual price override is in effect.
        gap_fill_applied: Whether a gap-fill discount was applied.
        orphan_day_discount: Whether an orphan-day discount was applied.
        last_minute_discount: Whether a last-minute discount was applied.
        far_future_premium: Whether a far-future premium was applied.
    """

    model_config = ConfigDict(extra="allow")

    user_override: bool | None = None
    gap_fill_applied: bool | None = None
    orphan_day_discount: bool | None = None
    last_minute_discount: bool | None = None
    far_future_premium: bool | None = None


class Thresholds(BaseModel):
    """Price floor, ceiling, and health metrics for a given day.

    Attributes:
        min_price: Minimum price floor (None if not set).
        max_price: Maximum price cap (None if not set).
        base_price: Base price before adjustments.
        health_score: Model confidence / health score (0–1).
    """

    model_config = ConfigDict(extra="allow")

    min_price: float | None = None
    max_price: float | None = None
    base_price: float | None = None
    health_score: float | None = None


class DebugInfo(BaseModel):
    """Internal pricing model debug metadata.

    Attributes:
        model_version: Version string of the pricing model.
        computed_at: ISO 8601 timestamp when the price was computed.
        signal_count: Number of signals used to compute the price.
        confidence: Confidence level (e.g. ``high``, ``medium``, ``low``).
    """

    model_config = ConfigDict(extra="allow")

    model_version: str | None = None
    computed_at: str | None = None
    signal_count: int | None = None
    confidence: str | None = None


class PriceReason(BaseModel):
    """Top-level pricing breakdown returned when ``reason=True`` is requested.

    Attributes:
        market_factors: Market-level pricing signals.
        pricing_customizations: User-applied customizations.
        thresholds: Min/max price thresholds and health score.
        debug_info: Internal model debug data.
    """

    model_config = ConfigDict(extra="allow")

    market_factors: MarketFactors | None = None
    pricing_customizations: PricingCustomizations | None = None
    thresholds: Thresholds | None = None
    debug_info: DebugInfo | None = None


class PriceDay(BaseModel):
    """Price and availability data for a single calendar day.

    Attributes:
        date: Calendar date in ``YYYY-MM-DD`` format.
        price: Recommended nightly price.
        user_price: User-overridden price, or None if not customized.
        uncustomized_price: Price before any user customizations.
        min_stay: Minimum stay length in nights.
        booking_status: Booking status (e.g. ``available``, ``booked``).
        booking_status_STLY: Same-time-last-year booking status.
        ADR: Average Daily Rate from historical data.
        ADR_STLY: Same-time-last-year ADR.
        unbookable: Non-zero when the day cannot be booked.
        booked_date: Date the stay was booked, or None if available.
        booked_date_STLY: Same-time-last-year booked date.
        weekly_discount: Weekly discount fraction (e.g. ``0.10`` for 10%).
        monthly_discount: Monthly discount fraction.
        extra_person_fee: Additional fee per extra guest.
        extra_person_fee_trigger: Guest count above which the extra fee applies.
        check_in: Whether check-in is permitted on this day.
        check_out: Whether check-out is permitted on this day.
        demand_color: Demand indicator colour (``green``, ``yellow``, ``red``).
        demand_desc: Human-readable demand description.
        reason: Structured pricing breakdown; populated when ``reason=True`` is requested.
    """

    date: str
    price: float
    user_price: float | None
    uncustomized_price: float | None
    min_stay: int
    booking_status: str | None
    booking_status_STLY: str | None = None
    ADR: float | None
    ADR_STLY: float | None = None
    unbookable: int | None
    booked_date: str | None
    booked_date_STLY: str | None = None
    weekly_discount: float | None
    monthly_discount: float | None
    extra_person_fee: float | None
    extra_person_fee_trigger: int | None = None
    check_in: bool | None
    check_out: bool | None
    demand_color: str | None
    demand_desc: str | None
    reason: PriceReason | None = None


class ListingPrices(BaseModel):
    """Prices for a single listing as returned by the API.

    When the API indicates an error for a listing (e.g. ``LISTING_NOT_PRESENT``),
    ``error_status`` is populated and ``data`` is empty rather than raising an
    exception.

    Attributes:
        id: Listing ID.
        pms: PMS name.
        group: Optional group name the listing belongs to.
        currency: ISO 4217 currency code.
        last_refreshed_at: ISO 8601 timestamp of the last price refresh.
        los_pricing: Length-of-stay pricing keyed by night count string.
        data: Per-day price records.
        error_status: Set when the API returned an error status for this listing.
    """

    id: str
    pms: str
    group: str | None
    currency: str
    last_refreshed_at: str | None
    los_pricing: dict[str, LOSPricing] | None
    data: list[PriceDay]
    error_status: str | None = None


class Prices:
    """Resource namespace for fetching listing prices and rate plans."""

    def __init__(self, http: HTTPClient) -> None:
        """Initialize with an HTTP client.

        Args:
            http: Configured HTTP transport client.
        """
        self._http = http

    def get(self, listings: list[PriceRequest], reason: bool = False) -> list[ListingPrices]:
        """Fetch prices for a list of listings.

        Posts to ``/v1/listing_prices``. Listings that the API marks with an
        error status (``LISTING_NOT_PRESENT``, ``LISTING_NO_DATA``,
        ``LISTING_TOGGLE_OFF``) are returned as ``ListingPrices`` objects with
        ``error_status`` set rather than raising an exception.

        Args:
            listings: Listings to fetch prices for.
            reason: When True, request pricing reason data in the response.

        Returns:
            One ``ListingPrices`` per input listing, in response order.
        """
        body: dict[str, Any] = {
            "listings": [r.model_dump(exclude_none=True) for r in listings]
        }
        logger.info("Fetching prices for %d listings", len(listings))
        raw = cast(
            list[dict[str, Any]], self._http.post("/v1/listing_prices", json=body, retryable=True)
        )
        result: list[ListingPrices] = []
        for item in raw:
            status = item.get("status")
            if status in _ERROR_STATUSES:
                logger.warning(
                    "Listing %s/%s has error status: %s", item.get("id"), item.get("pms"), status
                )
                lp = ListingPrices(
                    id=item["id"],
                    pms=item["pms"],
                    group=None,
                    currency="",
                    last_refreshed_at=None,
                    los_pricing=None,
                    data=[],
                    error_status=status,
                )
            else:
                lp = ListingPrices(**item)
            result.append(lp)
        error_count = sum(1 for lp in result if lp.error_status)
        logger.info("Received prices for %d listings (%d errors)", len(result), error_count)
        return result

    def rate_plans(self, listing_id: str | None = None, pms_name: str | None = None) -> list[dict]:
        """Fetch rate plans, optionally filtered by listing ID or PMS name.

        Sends a GET to ``/v1/fetch_rate_plans``.

        Args:
            listing_id: Filter results to this listing ID.
            pms_name: Filter results to this PMS name.

        Returns:
            List of rate plan dicts as returned by the API.
        """
        params: dict[str, str] = {}
        if listing_id is not None:
            params["listing_id"] = listing_id
        if pms_name is not None:
            params["pms_name"] = pms_name
        logger.info("Fetching rate plans listing_id=%s pms_name=%s", listing_id, pms_name)
        return cast(list[dict], self._http.get("/v1/fetch_rate_plans", params=params or None))
