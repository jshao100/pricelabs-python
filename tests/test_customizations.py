"""Tests for pricelabs.customizations."""

import json

import httpx

from pricelabs.customizations import ListingCustomizations

BASE_URL = "https://api.pricelabs.co"
LISTING_ID = "listing-abc"
PMS = "airbnb"
CUSTOMIZATIONS_PATH = "/v1/customizations/listing"

POPULATED_RESPONSE = {
    "customizations": {
        "seasonality_customization_on": True,
        "seasonality_type": "recommended",
        "last_min_factor_on": True,
        "last_min_factor_type": "linear_gradual",
        "last_min_factor_value": 15.5,
        "last_min_factor_dfd": 14,
        "dow_factor_on": True,
        "dow_factor_value_mon": -10,
        "dow_factor_value_tue": 0,
        "dow_factor_value_wed": 0,
        "dow_factor_value_thu": 5,
        "dow_factor_value_fri": 20,
        "dow_factor_value_sat": 25,
        "dow_factor_value_sun": 10,
        "far_out_premium_on": False,
        "far_out_premium_type": "fix",
        "far_out_premium_value": 30,
        "far_out_premium_start": 60,
        "far_out_premium_step": 10,
        "tone_demand_factor_on": True,
        "tone_demand_factor": "no demand factor",
        "hotel_compset_type": "recommended",
        "hotel_wt": "balance",
    }
}


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


def test_get_parses_populated_response(mock_client):
    """get() parses a populated customizations response into the model."""
    client, respx_mock = mock_client
    respx_mock.get(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json=POPULATED_RESPONSE)
    )

    result = client.customizations.get(LISTING_ID, PMS)

    assert result.dow_factor_value_fri == 20
    assert result.last_min_factor_type == "linear_gradual"
    assert result.tone_demand_factor == "no demand factor"
    assert result.far_out_premium_type == "fix"
    assert result.far_out_premium_on is False


def test_get_empty_customizations(mock_client):
    """get() on empty {} returns an all-None model without error."""
    client, respx_mock = mock_client
    respx_mock.get(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json={"customizations": {}})
    )

    result = client.customizations.get(LISTING_ID, PMS)

    assert result.seasonality_customization_on is None
    assert result.dow_factor_value_mon is None
    assert result.tone_demand_factor is None


def test_get_sends_correct_query_params(mock_client):
    """get() sends listing_id, pms_name, and toggled_on as query params."""
    client, respx_mock = mock_client
    respx_mock.get(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json={"customizations": {}})
    )

    client.customizations.get(LISTING_ID, PMS)

    req = respx_mock.calls.last.request
    url = str(req.url)
    assert f"listing_id={LISTING_ID}" in url
    assert f"pms_name={PMS}" in url
    assert "toggled_on=true" in url


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------


def test_update_posts_correct_body(mock_client):
    """update() POSTs the right body; None fields omitted, False bools kept."""
    client, respx_mock = mock_client
    respx_mock.post(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    model = ListingCustomizations(
        seasonality_customization_on=False,
        seasonality_type="aggressive",
        last_min_factor_on=True,
    )
    client.customizations.update(LISTING_ID, PMS, model)

    req = respx_mock.calls.last.request
    body = json.loads(req.content)
    assert body["listing_id"] == LISTING_ID
    assert body["pms_name"] == PMS
    cust = body["customizations"]
    assert cust["seasonality_customization_on"] is False
    assert cust["seasonality_type"] == "aggressive"
    assert cust["last_min_factor_on"] is True
    assert "dow_factor_on" not in cust


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def test_model_partial_round_trip():
    """Model accepts partial data and round-trips via model_dump."""
    model = ListingCustomizations(
        last_min_factor_on=True,
        last_min_factor_type="fixed",
        last_min_factor_value=20.0,
        last_min_factor_dfd=7,
    )
    dumped = model.model_dump(exclude_none=True)
    assert dumped == {
        "last_min_factor_on": True,
        "last_min_factor_type": "fixed",
        "last_min_factor_value": 20.0,
        "last_min_factor_dfd": 7,
    }
    restored = ListingCustomizations.model_validate(dumped)
    assert restored.last_min_factor_on is True
    assert restored.seasonality_type is None


# ---------------------------------------------------------------------------
# Client wiring
# ---------------------------------------------------------------------------


def test_client_customizations_property(mock_client):
    """client.customizations returns the Customizations resource."""
    client, _ = mock_client
    from pricelabs.customizations import Customizations

    assert isinstance(client.customizations, Customizations)
