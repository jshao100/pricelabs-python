"""Smoke tests verifying that all fixture files load and have expected top-level keys."""

from tests.conftest import load_fixture


def test_listings_fixture():
    """listings.json loads and contains 3 listings."""
    data = load_fixture("listings")
    assert "listings" in data
    assert len(data["listings"]) == 3


def test_listing_single_fixture():
    """listing_single.json loads and has expected top-level keys."""
    data = load_fixture("listing_single")
    assert "id" in data
    assert "pms" in data
    assert "name" in data


def test_listing_update_response_fixture():
    """listing_update_response.json loads and has listings array."""
    data = load_fixture("listing_update_response")
    assert "listings" in data
    assert len(data["listings"]) > 0
    listing = data["listings"][0]
    assert "id" in listing
    assert "min" in listing
    assert "base" in listing
    assert "max" in listing


def test_listing_prices_fixture():
    """listing_prices.json loads as array with expected keys."""
    data = load_fixture("listing_prices")
    assert isinstance(data, list)
    assert len(data) == 2
    entry = data[0]
    assert "id" in entry
    assert "pms" in entry
    assert "currency" in entry
    assert "data" in entry
    assert "los_pricing" in entry


def test_listing_prices_with_reason_fixture():
    """listing_prices_with_reason.json loads and has reason objects on price days."""
    data = load_fixture("listing_prices_with_reason")
    assert isinstance(data, list)
    assert len(data) == 2
    price_day = data[0]["data"][0]
    assert "reason" in price_day
    reason = price_day["reason"]
    assert "market_factors" in reason
    assert "pricing_customizations" in reason
    assert "thresholds" in reason
    assert "debug_info" in reason


def test_listing_prices_errors_fixture():
    """listing_prices_errors.json loads as array with error status entries."""
    data = load_fixture("listing_prices_errors")
    assert isinstance(data, list)
    assert len(data) == 2
    statuses = {e["status"] for e in data}
    assert "LISTING_NOT_PRESENT" in statuses
    assert "LISTING_TOGGLE_OFF" in statuses


def test_rate_plans_fixture():
    """rate_plans.json loads as array with rateplans object."""
    data = load_fixture("rate_plans")
    assert isinstance(data, list)
    assert len(data) == 1
    entry = data[0]
    assert "id" in entry
    assert "pms" in entry
    assert "rateplans" in entry


def test_overrides_fixture():
    """overrides.json loads and has 4 override entries."""
    data = load_fixture("overrides")
    assert "overrides" in data
    assert len(data["overrides"]) == 4


def test_neighborhood_data_fixture():
    """neighborhood_data.json loads with expected top-level keys."""
    data = load_fixture("neighborhood_data")
    assert "Listings Used" in data
    assert "currency" in data
    assert "lat" in data
    assert "lng" in data
    assert "Future Percentile Prices" in data
    assert "Summary Table Base Price" in data
    assert "Future Occ/New/Canc" in data


def test_reservations_page1_fixture():
    """reservations_page1.json loads with next_page=true and 3 reservations."""
    data = load_fixture("reservations_page1")
    assert "pms_name" in data
    assert "next_page" in data
    assert "data" in data
    assert data["next_page"] is True
    assert len(data["data"]) == 3


def test_reservations_page2_fixture():
    """reservations_page2.json loads with next_page=false and has a cancelled reservation."""
    data = load_fixture("reservations_page2")
    assert "next_page" in data
    assert data["next_page"] is False
    assert len(data["data"]) == 2
    statuses = {r["booking_status"] for r in data["data"]}
    assert "cancelled" in statuses


def test_error_401_fixture():
    """error_401.json loads with error and status fields."""
    data = load_fixture("error_401")
    assert "error" in data
    assert "status" in data
    assert data["status"] == 401


def test_error_429_fixture():
    """error_429.json loads with error and status fields."""
    data = load_fixture("error_429")
    assert "error" in data
    assert "status" in data
    assert data["status"] == 429


def test_error_404_fixture():
    """error_404.json loads with error and status fields."""
    data = load_fixture("error_404")
    assert "error" in data
    assert "status" in data
    assert data["status"] == 404
