"""End-to-end integration tests covering a full PriceLabs SDK workflow.

Mocks all HTTP with respx. Exercises:
  1. List listings
  2. Get prices for a listing
  3. Create overrides
  4. List overrides
  5. Auto-paginated reservations
  6. Get neighborhood data
"""

import logging

import httpx
import pytest

from pricelabs.listings import Listing
from pricelabs.market import NeighborhoodData
from pricelabs.overrides import DateSpecificOverride, OverrideInput
from pricelabs.prices import ListingPrices, PriceDay, PriceRequest
from pricelabs.reservations import Reservation
from tests.conftest import load_fixture

logger = logging.getLogger(__name__)

LISTING_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
PMS = "airbnb"


def test_full_workflow(mock_client):
    """Full workflow: listings → prices → overrides → reservations → neighborhood."""
    client, respx_mock = mock_client

    # Step 1: List listings — verify returns list[Listing]
    listings_fixture = load_fixture("listings")
    respx_mock.get("/v1/listings").mock(return_value=httpx.Response(200, json=listings_fixture))

    listings = client.listings.list()

    assert isinstance(listings, list)
    assert len(listings) > 0
    assert all(isinstance(item, Listing) for item in listings)
    assert listings[0].id == LISTING_ID
    assert listings[0].pms == PMS
    logger.info("Step 1 OK: %d listings returned", len(listings))

    # Step 2: Get prices — verify returns ListingPrices with PriceDay data
    prices_fixture = load_fixture("listing_prices")
    respx_mock.post("/v1/listing_prices").mock(
        return_value=httpx.Response(200, json=prices_fixture)
    )

    prices_result = client.prices.get([PriceRequest(id=LISTING_ID, pms=PMS)])

    assert isinstance(prices_result, list)
    assert len(prices_result) > 0
    lp = prices_result[0]
    assert isinstance(lp, ListingPrices)
    assert lp.id == LISTING_ID
    assert lp.pms == PMS
    assert lp.currency == "USD"
    assert len(lp.data) > 0
    assert isinstance(lp.data[0], PriceDay)
    assert lp.data[0].price > 0
    logger.info("Step 2 OK: %d price days", len(lp.data))

    # Step 3: Create overrides — verify returns list[DateSpecificOverride]
    overrides_fixture = load_fixture("overrides")
    respx_mock.post(f"/v1/listings/{LISTING_ID}/overrides").mock(
        return_value=httpx.Response(200, json=overrides_fixture)
    )

    new_overrides = [
        OverrideInput(
            date="2026-06-14",
            price="200",
            price_type="fixed",
            reason="Weekend event pricing",
        ),
    ]
    created = client.overrides.create(LISTING_ID, PMS, new_overrides)

    assert isinstance(created, list)
    assert len(created) > 0
    assert all(isinstance(o, DateSpecificOverride) for o in created)
    assert created[0].date == "2026-06-14"
    assert created[0].price == "200"
    logger.info("Step 3 OK: %d overrides created", len(created))

    # Step 4: List overrides — verify they match what was created
    respx_mock.get(f"/v1/listings/{LISTING_ID}/overrides").mock(
        return_value=httpx.Response(200, json=overrides_fixture)
    )

    listed = client.overrides.list(LISTING_ID, PMS)

    assert isinstance(listed, list)
    assert len(listed) == len(created)
    assert {o.date for o in listed} == {o.date for o in created}
    logger.info("Step 4 OK: %d overrides listed", len(listed))

    # Step 5: Auto-paginated reservations — verify yields Reservation objects across pages
    page1 = load_fixture("reservations_page1")
    page2 = load_fixture("reservations_page2")
    page_iter = iter([page1, page2])

    def _reservation_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(page_iter))

    respx_mock.get("/v1/reservation_data").mock(side_effect=_reservation_handler)

    all_reservations = list(client.reservations.list_all(
        pms="airbnb", start_date="2026-01-01", end_date="2026-12-31",
    ))

    expected_count = len(page1["data"]) + len(page2["data"])
    assert len(all_reservations) == expected_count
    assert all(isinstance(r, Reservation) for r in all_reservations)
    assert all_reservations[0].reservation_id == page1["data"][0]["reservation_id"]
    logger.info("Step 5 OK: %d reservations across 2 pages", len(all_reservations))

    # Step 6: Neighborhood data — verify returns NeighborhoodData
    neighborhood_raw = load_fixture("neighborhood_data")
    respx_mock.get("/v1/neighborhood_data").mock(
        return_value=httpx.Response(200, json={"data": neighborhood_raw})
    )

    neighborhood = client.market.neighborhood(LISTING_ID, PMS)

    assert isinstance(neighborhood, NeighborhoodData)
    assert neighborhood.listings_used == 350
    assert neighborhood.currency == "USD"
    assert neighborhood.lat == pytest.approx(39.8072)
    assert neighborhood.lng == pytest.approx(-86.1647)
    assert neighborhood.market_kpi is not None
    assert len(neighborhood.market_kpi.category) == 3
    logger.info("Step 6 OK: neighborhood=%s", neighborhood.neighborhood_data_source)


def test_prices_with_reason_breakdown(mock_client):
    """Prices with reason=True include market factors and thresholds per day."""
    client, respx_mock = mock_client

    prices_fixture = load_fixture("listing_prices_with_reason")
    respx_mock.post("/v1/listing_prices").mock(
        return_value=httpx.Response(200, json=prices_fixture)
    )

    result = client.prices.get([PriceRequest(id=LISTING_ID, pms=PMS, reason=True)])

    assert len(result) > 0
    lp = result[0]
    assert lp.error_status is None

    # At least one day should carry reason data
    days_with_reason = [d for d in lp.data if d.reason is not None]
    assert len(days_with_reason) > 0

    day = days_with_reason[0]
    assert day.reason is not None
    assert day.reason.market_factors is not None
    assert day.reason.thresholds is not None
    assert day.reason.thresholds.base_price == pytest.approx(175.0)


def test_reservations_pagination_yields_all_pages(mock_client):
    """list_all() fetches page 2 automatically when page 1 has next_page=True."""
    client, respx_mock = mock_client

    page1 = load_fixture("reservations_page1")
    page2 = load_fixture("reservations_page2")
    assert page1["next_page"] is True
    assert page2["next_page"] is False

    page_iter = iter([page1, page2])

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(page_iter))

    respx_mock.get("/v1/reservation_data").mock(side_effect=_handler)

    result = list(client.reservations.list_all(
        pms="airbnb", start_date="2026-01-01", end_date="2026-12-31",
    ))

    assert len(result) == len(page1["data"]) + len(page2["data"])
    # Page 2's reservations appear after page 1's
    last_reservation = result[-1]
    assert last_reservation.reservation_id == page2["data"][-1]["reservation_id"]


def test_overrides_delete(mock_client):
    """delete() calls DELETE on the correct endpoint without raising."""
    client, respx_mock = mock_client

    respx_mock.delete(f"/v1/listings/{LISTING_ID}/overrides").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )

    # delete() returns None; no exception means success
    client.overrides.delete(LISTING_ID, PMS, dates=["2026-06-14"])

    assert respx_mock.calls.last.request.method == "DELETE"
