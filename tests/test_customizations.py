"""Tests for pricelabs.customizations."""

import json

import httpx

from pricelabs.customizations import (
    DayOfWeekAdjustment,
    DemandFactor,
    FarOutPremium,
    LastMinutePrices,
    ListingCustomizations,
    Seasonality,
)

BASE_URL = "https://api.pricelabs.co"
LISTING_ID = "listing-abc"
PMS = "airbnb"
CUSTOMIZATIONS_PATH = "/v1/customizations/listing"

NESTED_RESPONSE = {
    "customizations": {
        "last_minute_prices": {
            "last_min_factor_on": True,
            "last_min_factor_type": "linear_gradual",
            "last_min_factor_value": 15.5,
            "last_min_factor_dfd": 14,
        },
        "far_out_premium": {
            "far_out_premium_on": True,
            "far_out_premium_type": "fix",
            "far_out_premium_value": 30,
            "far_out_premium_start": 60,
            "far_out_premium_step": 10,
        },
    }
}


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


def test_get_parses_nested_response(mock_client):
    """get() parses nested sub-objects and leaves absent ones as None."""
    client, respx_mock = mock_client
    respx_mock.get(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json=NESTED_RESPONSE)
    )

    result = client.customizations.get(LISTING_ID, PMS)

    assert result.last_minute_prices is not None
    assert result.last_minute_prices.last_min_factor_type == "linear_gradual"
    assert result.last_minute_prices.last_min_factor_value == 15.5
    assert result.far_out_premium is not None
    assert result.far_out_premium.far_out_premium_on is True
    assert result.far_out_premium.far_out_premium_type == "fix"
    assert result.seasonality is None
    assert result.day_of_week_adjustment is None
    assert result.demand_factor is None


def test_get_empty_customizations(mock_client):
    """get() on empty {} returns a container with all sub-objects None."""
    client, respx_mock = mock_client
    respx_mock.get(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json={"customizations": {}})
    )

    result = client.customizations.get(LISTING_ID, PMS)

    assert result.last_minute_prices is None
    assert result.seasonality is None
    assert result.day_of_week_adjustment is None
    assert result.far_out_premium is None
    assert result.demand_factor is None


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


def test_update_posts_nested_body_only_set_subobject(mock_client):
    """update() nests under customizations; absent sub-objects are omitted."""
    client, respx_mock = mock_client
    respx_mock.post(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    model = ListingCustomizations(
        last_minute_prices=LastMinutePrices(
            last_min_factor_on=True,
            last_min_factor_type="linear",
            last_min_factor_value=10.0,
        ),
    )
    client.customizations.update(LISTING_ID, PMS, model)

    req = respx_mock.calls.last.request
    body = json.loads(req.content)
    assert body["listing_id"] == LISTING_ID
    assert body["pms_name"] == PMS
    cust = body["customizations"]
    assert "last_minute_prices" in cust
    assert cust["last_minute_prices"]["last_min_factor_on"] is True
    assert cust["last_minute_prices"]["last_min_factor_type"] == "linear"
    assert "seasonality" not in cust
    assert "day_of_week_adjustment" not in cust
    assert "far_out_premium" not in cust
    assert "demand_factor" not in cust


def test_update_keeps_false_on_flag(mock_client):
    """update() includes False *_on flags (not dropped by exclude_none)."""
    client, respx_mock = mock_client
    respx_mock.post(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    model = ListingCustomizations(
        seasonality=Seasonality(
            seasonality_customization_on=False,
            seasonality_type="aggressive",
        ),
    )
    client.customizations.update(LISTING_ID, PMS, model)

    req = respx_mock.calls.last.request
    body = json.loads(req.content)
    cust = body["customizations"]
    assert cust["seasonality"]["seasonality_customization_on"] is False
    assert cust["seasonality"]["seasonality_type"] == "aggressive"


def test_update_partial_subobject_omits_none_fields(mock_client):
    """A partial sub-object omits fields that were not set."""
    client, respx_mock = mock_client
    respx_mock.post(f"{BASE_URL}{CUSTOMIZATIONS_PATH}").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    model = ListingCustomizations(
        last_minute_prices=LastMinutePrices(
            last_min_factor_on=True,
            last_min_factor_type="fixed",
        ),
    )
    client.customizations.update(LISTING_ID, PMS, model)

    req = respx_mock.calls.last.request
    body = json.loads(req.content)
    lmp = body["customizations"]["last_minute_prices"]
    assert lmp == {"last_min_factor_on": True, "last_min_factor_type": "fixed"}
    assert "last_min_factor_value" not in lmp
    assert "last_min_factor_dfd" not in lmp


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def test_model_nested_round_trip():
    """Container round-trips nested data via model_dump/model_validate."""
    model = ListingCustomizations(
        last_minute_prices=LastMinutePrices(
            last_min_factor_on=True,
            last_min_factor_type="fixed",
            last_min_factor_value=20.0,
            last_min_factor_dfd=7,
        ),
        demand_factor=DemandFactor(
            tone_demand_factor_on=True,
            tone_demand_factor="no demand factor",
        ),
    )
    dumped = model.model_dump(exclude_none=True)
    assert dumped == {
        "last_minute_prices": {
            "last_min_factor_on": True,
            "last_min_factor_type": "fixed",
            "last_min_factor_value": 20.0,
            "last_min_factor_dfd": 7,
        },
        "demand_factor": {
            "tone_demand_factor_on": True,
            "tone_demand_factor": "no demand factor",
        },
    }
    restored = ListingCustomizations.model_validate(dumped)
    assert restored.last_minute_prices.last_min_factor_on is True
    assert restored.demand_factor.tone_demand_factor == "no demand factor"
    assert restored.seasonality is None


def test_submodels_construct_independently():
    """Each sub-model can be constructed and dumped independently."""
    dow = DayOfWeekAdjustment(dow_factor_on=True, dow_factor_value_fri=20)
    dumped = dow.model_dump(exclude_none=True)
    assert dumped == {"dow_factor_on": True, "dow_factor_value_fri": 20}

    fop = FarOutPremium(far_out_premium_on=False, far_out_premium_type="fix")
    dumped = fop.model_dump(exclude_none=True)
    assert dumped == {"far_out_premium_on": False, "far_out_premium_type": "fix"}

    sea = Seasonality(seasonality_customization_on=True)
    dumped = sea.model_dump(exclude_none=True)
    assert dumped == {"seasonality_customization_on": True}


# ---------------------------------------------------------------------------
# Client wiring
# ---------------------------------------------------------------------------


def test_client_customizations_property(mock_client):
    """client.customizations returns the Customizations resource."""
    client, _ = mock_client
    from pricelabs.customizations import Customizations

    assert isinstance(client.customizations, Customizations)
