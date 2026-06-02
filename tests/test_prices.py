"""Tests for pricelabs.prices."""

import json

import httpx
import respx

from pricelabs.prices import (
    DebugInfo,
    ListingPrices,
    LOSPricing,
    MarketFactors,
    PriceDay,
    PriceReason,
    PriceRequest,
    Prices,
    PricingCustomizations,
    Thresholds,
)
from tests.conftest import load_fixture

BASE_URL = "https://api.pricelabs.co"

_LISTING_A = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_LISTING_B = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
_ERROR_A = "d4e5f6a7-b8c9-0123-def0-234567890123"
_ERROR_B = "e5f6a7b8-c9d0-1234-ef01-345678901234"


# ---------------------------------------------------------------------------
# PriceRequest serialization
# ---------------------------------------------------------------------------


def test_price_request_serialization_minimal():
    """PriceRequest with only required fields excludes None values when serialized."""
    req = PriceRequest(id="abc", pms="airbnb")
    data = req.model_dump(exclude_none=True)
    assert data == {"id": "abc", "pms": "airbnb", "reason": False}


def test_price_request_serialization_full():
    """PriceRequest with all fields serializes correctly."""
    req = PriceRequest(
        id="abc", pms="airbnb", date_from="2026-06-01", date_to="2026-06-30", reason=True
    )
    data = req.model_dump(exclude_none=True)
    assert data["date_from"] == "2026-06-01"
    assert data["date_to"] == "2026-06-30"
    assert data["reason"] is True


def test_price_request_defaults():
    """PriceRequest optional fields default to None/False."""
    req = PriceRequest(id="x", pms="ownerrez")
    assert req.date_from is None
    assert req.date_to is None
    assert req.reason is False


# ---------------------------------------------------------------------------
# get() — happy path
# ---------------------------------------------------------------------------


@respx.mock
def test_get_parses_listing_prices(mock_client):
    """get() returns a list of ListingPrices with populated PriceDay data."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    requests = [
        PriceRequest(id=_LISTING_A, pms="airbnb"),
        PriceRequest(id=_LISTING_B, pms="ownerrez"),
    ]
    results = client.prices.get(requests)

    assert len(results) == 2
    first = results[0]
    assert isinstance(first, ListingPrices)
    assert first.id == _LISTING_A
    assert first.pms == "airbnb"
    assert first.currency == "USD"
    assert first.group == "San Francisco Properties"
    assert first.error_status is None


def test_get_parses_price_days(mock_client):
    """get() correctly parses PriceDay records including optional fields."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_A, pms="airbnb")])
    days = results[0].data

    assert len(days) == 5
    day = days[0]
    assert isinstance(day, PriceDay)
    assert day.date == "2026-06-01"
    assert day.price == 175.0
    assert day.user_price is None
    assert day.booking_status == "available"
    assert day.demand_color == "green"
    assert day.check_in is True
    assert day.reason is None
    # fields absent from fixture default to None
    assert day.booking_status_STLY is None
    assert day.ADR_STLY is None


def test_get_parses_los_pricing(mock_client):
    """get() correctly parses LOSPricing objects from the response."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_A, pms="airbnb")])
    los = results[0].los_pricing

    assert los is not None
    assert "1" in los
    entry = los["1"]
    assert isinstance(entry, LOSPricing)
    assert entry.los_night == 1
    assert entry.max_price == 200.0
    assert entry.min_price == 150.0
    assert entry.los_adjustment == 0.0


def test_get_listing_with_null_group(mock_client):
    """get() parses a listing with a null group field."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_B, pms="ownerrez")])
    assert results[1].group is None


def test_get_sends_correct_post_body(mock_client):
    """get() posts the listings array to /v1/listing_prices."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices")
    route = respx_mock.post("/v1/listing_prices").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    requests = [PriceRequest(id="abc", pms="airbnb", date_from="2026-06-01")]
    client.prices.get(requests)

    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert "listings" in body
    assert body["listings"][0]["id"] == "abc"
    assert body["listings"][0]["dateFrom"] == "2026-06-01"


# ---------------------------------------------------------------------------
# get() — error statuses
# ---------------------------------------------------------------------------


def test_get_handles_listing_not_present(mock_client):
    """get() returns ListingPrices with error_status for LISTING_NOT_PRESENT."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_errors")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    requests = [
        PriceRequest(id=_ERROR_A, pms="airbnb"),
        PriceRequest(id=_ERROR_B, pms="ownerrez"),
    ]
    results = client.prices.get(requests)

    assert len(results) == 2
    not_present = results[0]
    assert isinstance(not_present, ListingPrices)
    assert not_present.error_status == "LISTING_NOT_PRESENT"
    assert not_present.id == _ERROR_A
    assert not_present.data == []


def test_get_handles_listing_toggle_off(mock_client):
    """get() returns ListingPrices with error_status for LISTING_TOGGLE_OFF."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_errors")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_ERROR_B, pms="ownerrez")])
    toggle_off = results[1]
    assert toggle_off.error_status == "LISTING_TOGGLE_OFF"
    assert toggle_off.los_pricing is None
    assert toggle_off.last_refreshed_at is None


# ---------------------------------------------------------------------------
# rate_plans()
# ---------------------------------------------------------------------------


def test_rate_plans_returns_data(mock_client):
    """rate_plans() returns parsed rate plan dicts from the API."""
    client, respx_mock = mock_client
    fixture = load_fixture("rate_plans")
    respx_mock.get("/v1/fetch_rate_plans").mock(return_value=httpx.Response(200, json=fixture))

    result = client.prices.rate_plans()

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == _LISTING_A
    assert result[0]["pms"] == "airbnb"


def test_rate_plans_sends_listing_id_param(mock_client):
    """rate_plans() includes listing_id as a query parameter when provided."""
    client, respx_mock = mock_client
    fixture = load_fixture("rate_plans")
    route = respx_mock.get("/v1/fetch_rate_plans").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    client.prices.rate_plans(listing_id="abc123")

    url = str(route.calls.last.request.url)
    assert "listing_id=abc123" in url


def test_rate_plans_sends_pms_name_param(mock_client):
    """rate_plans() includes pms_name as a query parameter when provided."""
    client, respx_mock = mock_client
    fixture = load_fixture("rate_plans")
    route = respx_mock.get("/v1/fetch_rate_plans").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    client.prices.rate_plans(pms_name="airbnb")

    url = str(route.calls.last.request.url)
    assert "pms_name=airbnb" in url


def test_rate_plans_sends_both_params(mock_client):
    """rate_plans() includes both query params when both are provided."""
    client, respx_mock = mock_client
    fixture = load_fixture("rate_plans")
    route = respx_mock.get("/v1/fetch_rate_plans").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    client.prices.rate_plans(listing_id="xyz", pms_name="ownerrez")

    url = str(route.calls.last.request.url)
    assert "listing_id=xyz" in url
    assert "pms_name=ownerrez" in url


def test_rate_plans_no_params_sends_no_query_string(mock_client):
    """rate_plans() with no args sends no query params."""
    client, respx_mock = mock_client
    fixture = load_fixture("rate_plans")
    route = respx_mock.get("/v1/fetch_rate_plans").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    client.prices.rate_plans()

    url = str(route.calls.last.request.url)
    assert "listing_id" not in url
    assert "pms_name" not in url


# ---------------------------------------------------------------------------
# client.prices property
# ---------------------------------------------------------------------------


def test_client_prices_property_returns_prices_instance(mock_client):
    """client.prices returns a Prices instance."""
    client, _ = mock_client
    assert isinstance(client.prices, Prices)


# ---------------------------------------------------------------------------
# PriceReason models
# ---------------------------------------------------------------------------


@respx.mock
def test_price_reason_parses_from_fixture(mock_client):
    """PriceDay.reason parses into a PriceReason instance from the fixture."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_with_reason")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_A, pms="airbnb", reason=True)])
    day = results[0].data[0]

    assert isinstance(day.reason, PriceReason)


@respx.mock
def test_price_reason_nested_market_factors(mock_client):
    """price_day.reason.market_factors is a MarketFactors instance with expected values."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_with_reason")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_A, pms="airbnb", reason=True)])
    reason = results[0].data[0].reason

    assert isinstance(reason.market_factors, MarketFactors)
    assert reason.market_factors.seasonality_score == 0.82
    assert reason.market_factors.day_of_week_multiplier == 1.15
    assert reason.market_factors.lead_time_days == 2
    assert reason.market_factors.supply_demand_ratio == 0.73
    assert reason.market_factors.local_events == ["Pride Parade", "Tech Conference"]


@respx.mock
def test_price_reason_nested_pricing_customizations(mock_client):
    """price_day.reason.pricing_customizations is a PricingCustomizations instance."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_with_reason")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_A, pms="airbnb", reason=True)])
    reason = results[0].data[0].reason

    assert isinstance(reason.pricing_customizations, PricingCustomizations)
    assert reason.pricing_customizations.user_override is False
    assert reason.pricing_customizations.gap_fill_applied is False
    assert reason.pricing_customizations.last_minute_discount is False
    assert reason.pricing_customizations.far_future_premium is False


@respx.mock
def test_price_reason_nested_thresholds(mock_client):
    """price_day.reason.thresholds is a Thresholds instance with expected values."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_with_reason")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_A, pms="airbnb", reason=True)])
    reason = results[0].data[0].reason

    assert isinstance(reason.thresholds, Thresholds)
    assert reason.thresholds.min_price == 85
    assert reason.thresholds.max_price == 450
    assert reason.thresholds.health_score == 0.91


@respx.mock
def test_price_reason_nested_debug_info(mock_client):
    """price_day.reason.debug_info is a DebugInfo instance with expected values."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_with_reason")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_A, pms="airbnb", reason=True)])
    reason = results[0].data[0].reason

    assert isinstance(reason.debug_info, DebugInfo)
    assert reason.debug_info.model_version == "v3.2.1"
    assert reason.debug_info.signal_count == 14
    assert reason.debug_info.confidence == "high"


@respx.mock
def test_price_reason_null_thresholds(mock_client):
    """Thresholds with null min_price and max_price parse correctly."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_prices_with_reason")
    respx_mock.post("/v1/listing_prices").mock(return_value=httpx.Response(200, json=fixture))

    results = client.prices.get([PriceRequest(id=_LISTING_B, pms="ownerrez", reason=True)])
    reason = results[1].data[0].reason

    assert isinstance(reason.thresholds, Thresholds)
    assert reason.thresholds.min_price is None
    assert reason.thresholds.max_price is None


def test_price_day_reason_none_still_parses():
    """PriceDay with reason=None parses without error."""
    day = PriceDay(
        date="2026-06-01",
        price=150.0,
        user_price=None,
        uncustomized_price=150.0,
        min_stay=1,
        booking_status="available",
        ADR=155.0,
        unbookable=0,
        booked_date=None,
        weekly_discount=None,
        monthly_discount=None,
        extra_person_fee=None,
        check_in=True,
        check_out=True,
        demand_color="green",
        demand_desc="High demand",
        reason=None,
    )
    assert day.reason is None


def test_price_reason_extra_fields_allowed():
    """PriceReason and sub-models accept extra fields without validation errors."""
    reason = PriceReason.model_validate({
        "market_factors": {"seasonality_score": 0.5, "unknown_future_field": "value"},
        "pricing_customizations": {"user_override": True, "new_flag": 42},
        "thresholds": {"min_price": 80, "extra_threshold": True},
        "debug_info": {"confidence": "high", "extra_key": "data"},
        "future_top_level": "ignored",
    })
    assert reason.market_factors.seasonality_score == 0.5
    assert reason.pricing_customizations.user_override is True
    assert reason.thresholds.min_price == 80
    assert reason.debug_info.confidence == "high"
