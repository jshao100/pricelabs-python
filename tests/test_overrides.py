"""Tests for pricelabs.overrides."""

import json

import httpx
import pytest

from pricelabs.overrides import OverrideInput
from tests.conftest import load_fixture

BASE_URL = "https://api.pricelabs.co"
LISTING_ID = "listing-abc"
PMS = "airbnb"
OVERRIDES_PATH = f"/v1/listings/{LISTING_ID}/overrides"


# ---------------------------------------------------------------------------
# list()
# ---------------------------------------------------------------------------


def test_list_sends_correct_get(mock_client):
    """list() sends GET with the pms query parameter."""
    client, respx_mock = mock_client
    fixture = load_fixture("overrides")
    respx_mock.get(f"{BASE_URL}{OVERRIDES_PATH}").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    client.overrides.list(LISTING_ID, PMS)

    req = respx_mock.calls.last.request
    assert req.method == "GET"
    assert f"pms={PMS}" in str(req.url)


def test_list_parses_all_override_types(mock_client):
    """list() correctly parses all 4 override types from the fixture."""
    client, respx_mock = mock_client
    fixture = load_fixture("overrides")
    respx_mock.get(f"{BASE_URL}{OVERRIDES_PATH}").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    result = client.overrides.list(LISTING_ID, PMS)

    assert len(result) == 4

    # fixed price override
    fixed = next(o for o in result if o.date == "2026-06-14")
    assert fixed.price == "200"
    assert fixed.price_type == "fixed"
    assert fixed.min_stay == 2
    assert fixed.currency == "USD"
    assert fixed.check_in_check_out_enabled == "0"
    assert fixed.reason == "Weekend event pricing"

    # percent price override with min/max prices (API returns them as strings)
    percent = next(o for o in result if o.date == "2026-07-04")
    assert percent.price_type == "percent"
    assert percent.min_price == pytest.approx(150.0)
    assert percent.max_price == pytest.approx(400.0)

    # check-in/out enabled override
    checkin = next(o for o in result if o.date == "2026-06-21")
    assert checkin.check_in_check_out_enabled == "1"
    assert checkin.check_in == "1111100"
    assert checkin.check_out == "1111111"

    # minimal override (many nulls)
    minimal = next(o for o in result if o.date == "2026-08-15")
    assert minimal.price_type is None
    assert minimal.min_stay is None
    assert minimal.reason is None


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


def test_create_sends_correct_post_body(mock_client):
    """create() sends POST with serialized OverrideInput list in the body."""
    client, respx_mock = mock_client
    fixture = load_fixture("overrides")
    respx_mock.post(f"{BASE_URL}{OVERRIDES_PATH}").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    inp = OverrideInput(date="2026-09-01", price="300", price_type="fixed", min_stay=2)
    client.overrides.create(LISTING_ID, PMS, [inp])

    req = respx_mock.calls.last.request
    assert req.method == "POST"
    body = json.loads(req.content)
    assert body["pms"] == PMS
    assert body["update_children"] is False
    assert len(body["overrides"]) == 1
    override_body = body["overrides"][0]
    assert override_body["date"] == "2026-09-01"
    assert override_body["price"] == "300"
    assert override_body["price_type"] == "fixed"
    assert override_body["min_stay"] == 2
    # None fields should be excluded
    assert "reason" not in override_body


def test_create_passes_update_children_flag(mock_client):
    """create() includes update_children=True in the POST body when set."""
    client, respx_mock = mock_client
    fixture = load_fixture("overrides")
    respx_mock.post(f"{BASE_URL}{OVERRIDES_PATH}").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    inp = OverrideInput(date="2026-09-01")
    client.overrides.create(LISTING_ID, PMS, [inp], update_children=True)

    body = json.loads(respx_mock.calls.last.request.content)
    assert body["update_children"] is True


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


def test_delete_sends_correct_body(mock_client):
    """delete() sends DELETE with date list formatted as [{"date": ...}]."""
    client, respx_mock = mock_client
    respx_mock.delete(f"{BASE_URL}{OVERRIDES_PATH}").mock(
        return_value=httpx.Response(204)
    )

    dates = ["2026-06-14", "2026-07-04"]
    client.overrides.delete(LISTING_ID, PMS, dates)

    req = respx_mock.calls.last.request
    assert req.method == "DELETE"
    body = json.loads(req.content)
    assert body["pms"] == PMS
    assert body["update_children"] is False
    assert body["overrides"] == [{"date": "2026-06-14"}, {"date": "2026-07-04"}]


def test_delete_handles_204(mock_client):
    """delete() returns None on a 204 empty response."""
    client, respx_mock = mock_client
    respx_mock.delete(f"{BASE_URL}{OVERRIDES_PATH}").mock(
        return_value=httpx.Response(204)
    )

    result = client.overrides.delete(LISTING_ID, PMS, ["2026-06-14"])
    assert result is None
