"""Tests for pricelabs.listings."""

import json

import httpx
import pytest

from pricelabs.listings import Listing, Listings, ListingUpdate
from tests.conftest import load_fixture

LISTING_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


# ---------------------------------------------------------------------------
# list()
# ---------------------------------------------------------------------------


def test_list_returns_parsed_listings(mock_client):
    """list() parses the response into a list of Listing objects."""
    client, respx_mock = mock_client
    fixture = load_fixture("listings")
    respx_mock.get("/v1/listings").mock(return_value=httpx.Response(200, json=fixture))

    result = client.listings.list()

    assert len(result) == 3
    assert all(isinstance(r, Listing) for r in result)
    assert result[0].id == LISTING_ID
    assert result[0].pms == "airbnb"
    assert result[0].name == "Cozy Downtown Loft - 2BR"
    assert result[0].latitude == pytest.approx(37.7749)
    assert result[0].longitude == pytest.approx(-122.4194)
    assert result[0].no_of_bedrooms == 2
    assert result[0].min == 85.0
    assert result[0].base == 175.0
    assert result[0].max == 450.0
    assert result[0].recommended_base_price == "180"
    assert result[0].isHidden is False
    assert result[0].push_enabled is True


def test_list_default_query_params(mock_client):
    """list() with defaults sends skip_hidden=false and only_syncing_listings=false."""
    client, respx_mock = mock_client
    fixture = load_fixture("listings")
    respx_mock.get("/v1/listings").mock(return_value=httpx.Response(200, json=fixture))

    client.listings.list()

    url = str(respx_mock.calls.last.request.url)
    assert "skip_hidden=false" in url
    assert "only_syncing_listings=false" in url


def test_list_skip_hidden_query_param(mock_client):
    """list(skip_hidden=True) sends skip_hidden=true in query params."""
    client, respx_mock = mock_client
    fixture = load_fixture("listings")
    respx_mock.get("/v1/listings").mock(return_value=httpx.Response(200, json=fixture))

    client.listings.list(skip_hidden=True)

    url = str(respx_mock.calls.last.request.url)
    assert "skip_hidden=true" in url
    assert "only_syncing_listings=false" in url


def test_list_only_syncing_query_param(mock_client):
    """list(only_syncing=True) sends only_syncing_listings=true in query params."""
    client, respx_mock = mock_client
    fixture = load_fixture("listings")
    respx_mock.get("/v1/listings").mock(return_value=httpx.Response(200, json=fixture))

    client.listings.list(only_syncing=True)

    url = str(respx_mock.calls.last.request.url)
    assert "only_syncing_listings=true" in url


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


def test_get_returns_parsed_listing(mock_client):
    """get() sends the correct path and parses the single-listing response."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_single")
    respx_mock.get(f"/v1/listings/{LISTING_ID}").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    result = client.listings.get(LISTING_ID)

    assert isinstance(result, Listing)
    assert result.id == LISTING_ID
    assert result.pms == "airbnb"
    assert result.city_name == "San Francisco"
    assert len(result.channel_listing_details) == 2
    assert result.channel_listing_details[0].channel_name == "airbnb"
    assert result.channel_listing_details[0].channel_listing_id == "12345678"


def test_get_correct_path(mock_client):
    """get() constructs the correct URL path."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_single")
    respx_mock.get(f"/v1/listings/{LISTING_ID}").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    client.listings.get(LISTING_ID)

    url = str(respx_mock.calls.last.request.url)
    assert f"/v1/listings/{LISTING_ID}" in url


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------


def test_update_sends_correct_post_body(mock_client):
    """update() POSTs a listings array and is retryable."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_update_response")
    respx_mock.post("/v1/listings").mock(return_value=httpx.Response(200, json=fixture))

    updates = [ListingUpdate(id=LISTING_ID, pms="airbnb", min=75, base=150, max=500)]
    result = client.listings.update(updates)

    body = json.loads(respx_mock.calls.last.request.content)
    assert body == {
        "listings": [{"id": LISTING_ID, "pms": "airbnb", "min": 75.0, "base": 150.0, "max": 500.0}]
    }
    assert result == fixture["listings"]


def test_update_excludes_none_fields(mock_client):
    """update() excludes None-valued fields from the request body."""
    client, respx_mock = mock_client
    fixture = load_fixture("listing_update_response")
    respx_mock.post("/v1/listings").mock(return_value=httpx.Response(200, json=fixture))

    updates = [ListingUpdate(id=LISTING_ID, pms="airbnb")]
    client.listings.update(updates)

    body = json.loads(respx_mock.calls.last.request.content)
    listing_body = body["listings"][0]
    assert "min" not in listing_body
    assert "base" not in listing_body
    assert "max" not in listing_body
    assert "tags" not in listing_body


# ---------------------------------------------------------------------------
# import_from_pms()
# ---------------------------------------------------------------------------


def test_import_from_pms_sends_correct_body(mock_client):
    """import_from_pms() POSTs the correct body and is not retryable."""
    client, respx_mock = mock_client
    response_data = {"status": "ok", "message": "listing imported"}
    respx_mock.post("/v1/add_listing_data").mock(
        return_value=httpx.Response(200, json=response_data)
    )

    result = client.listings.import_from_pms(LISTING_ID, "airbnb")

    body = json.loads(respx_mock.calls.last.request.content)
    assert body == {"listing_id": LISTING_ID, "pms_name": "airbnb"}
    assert result == response_data


# ---------------------------------------------------------------------------
# Listing model edge cases
# ---------------------------------------------------------------------------


def test_listing_minimal_fields():
    """Listing model handles an object with only required fields."""
    data = {"id": "minimal-id", "pms": "airbnb"}
    listing = Listing.model_validate(data)

    assert listing.id == "minimal-id"
    assert listing.pms == "airbnb"
    assert listing.name is None
    assert listing.latitude is None
    assert listing.longitude is None
    assert listing.min is None
    assert listing.channel_listing_details == []
    assert listing.isHidden is False
    assert listing.push_enabled is False
    assert listing.stly_revenue_past_7 is None


def test_listing_hidden():
    """Listing model correctly parses a hidden listing."""
    fixture = load_fixture("listings")
    hidden = next(item for item in fixture["listings"] if item.get("isHidden"))

    listing = Listing.model_validate(hidden)

    assert listing.isHidden is True
    assert listing.push_enabled is False
    assert listing.id == "c3d4e5f6-a7b8-9012-cdef-123456789012"


def test_listing_recommended_base_price_coercion():
    """recommended_base_price is coerced from int to str."""
    data = {"id": "x", "pms": "airbnb", "recommended_base_price": 180}
    listing = Listing.model_validate(data)

    assert listing.recommended_base_price == "180"


def test_listing_recommended_base_price_none():
    """recommended_base_price is None when missing from response."""
    data = {"id": "x", "pms": "airbnb"}
    listing = Listing.model_validate(data)

    assert listing.recommended_base_price is None


# ---------------------------------------------------------------------------
# Listings property on client
# ---------------------------------------------------------------------------


def test_client_listings_property_returns_listings_instance(mock_client):
    """client.listings returns a Listings instance."""
    client, _ = mock_client
    assert isinstance(client.listings, Listings)


def test_client_listings_property_cached(mock_client):
    """client.listings returns the same instance on repeated access."""
    client, _ = mock_client
    first = client.listings
    second = client.listings
    assert first is second
