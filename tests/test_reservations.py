"""Tests for the Reservations resource namespace."""

import httpx

from tests.conftest import load_fixture

# ---------------------------------------------------------------------------
# list() — response parsing
# ---------------------------------------------------------------------------


def test_list_parses_page(mock_client):
    """list() returns a Page[Reservation] with correct data and metadata."""
    client, respx_mock = mock_client
    fixture = load_fixture("reservations_page1")
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=fixture))

    page = client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")

    assert len(page.data) == 3
    assert page.next_page is True
    assert page.pms_name == "airbnb"


def test_list_parses_reservation_fields(mock_client):
    """list() correctly maps all standard fields on a booked reservation."""
    client, respx_mock = mock_client
    fixture = load_fixture("reservations_page1")
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=fixture))

    page = client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")
    r = page.data[0]

    assert r.listing_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert r.listing_name == "Cozy Downtown Loft - 2BR"
    assert r.reservation_id == "r1a2b3c4-d5e6-7890-abcd-ef1234567890"
    assert r.check_in == "2026-06-10"
    assert r.check_out == "2026-06-14"
    assert r.booking_status == "booked"
    assert r.rental_revenue == 700.00
    assert r.total_cost == 735.00
    assert r.no_of_days == 4
    assert r.currency == "USD"
    assert r.cleaning_fees == 85.00
    assert r.booking_channel == "Airbnb"
    assert r.channelConfirmationCode == "HMXYZ12345"
    assert r.cancelled_on is None


# ---------------------------------------------------------------------------
# list() — query params
# ---------------------------------------------------------------------------


def test_list_passes_required_default_params(mock_client):
    """list() always sends limit, offset, and include_hidden query params."""
    client, respx_mock = mock_client
    fixture = load_fixture("reservations_page1")
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=fixture))

    client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")

    url = str(respx_mock.calls.last.request.url)
    assert "limit=100" in url
    assert "offset=0" in url
    assert "include_hidden=false" in url.lower()


def test_list_passes_optional_params(mock_client):
    """list() forwards optional filter params to the request URL."""
    client, respx_mock = mock_client
    fixture = load_fixture("reservations_page1")
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=fixture))

    client.reservations.list(
        pms="airbnb",
        listing_id="abc123",
        start_date="2026-06-01",
        end_date="2026-06-30",
        limit=50,
        offset=10,
    )

    url = str(respx_mock.calls.last.request.url)
    assert "pms=airbnb" in url
    assert "listing_id=abc123" in url
    assert "start_date=2026-06-01" in url
    assert "end_date=2026-06-30" in url
    assert "limit=50" in url
    assert "offset=10" in url


def test_list_omits_optional_params(mock_client):
    """list() does not send listing_id when not provided."""
    client, respx_mock = mock_client
    fixture = load_fixture("reservations_page1")
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=fixture))

    client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")

    url = str(respx_mock.calls.last.request.url)
    assert "pms=airbnb" in url
    assert "start_date=2026-01-01" in url
    assert "end_date=2026-12-31" in url
    assert "listing_id=" not in url


# ---------------------------------------------------------------------------
# list_all() — auto-pagination
# ---------------------------------------------------------------------------


def test_list_all_iterates_two_pages(mock_client):
    """list_all() yields all items across two pages."""
    client, respx_mock = mock_client
    page1 = load_fixture("reservations_page1")
    page2 = load_fixture("reservations_page2")

    responses = iter([
        httpx.Response(200, json=page1),
        httpx.Response(200, json=page2),
    ])
    respx_mock.get("/v1/reservation_data").mock(side_effect=lambda req: next(responses))

    results = list(client.reservations.list_all(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31", limit=3))

    assert len(results) == 5  # 3 from page1 + 2 from page2
    assert results[0].reservation_id == "r1a2b3c4-d5e6-7890-abcd-ef1234567890"
    assert results[3].reservation_id == "r4d5e6f7-a8b9-0123-def0-234567890123"
    assert respx_mock.calls.call_count == 2


def test_list_all_increments_offset(mock_client):
    """list_all() increments offset by limit between pages."""
    client, respx_mock = mock_client
    page1 = load_fixture("reservations_page1")
    page2 = load_fixture("reservations_page2")

    responses = iter([
        httpx.Response(200, json=page1),
        httpx.Response(200, json=page2),
    ])
    respx_mock.get("/v1/reservation_data").mock(side_effect=lambda req: next(responses))

    list(client.reservations.list_all(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31", limit=3))

    first_url = str(respx_mock.calls[0].request.url)
    second_url = str(respx_mock.calls[1].request.url)
    assert "offset=0" in first_url
    assert "offset=3" in second_url


def test_list_all_stops_when_next_page_false(mock_client):
    """list_all() makes exactly one request when next_page is False."""
    client, respx_mock = mock_client
    page2 = load_fixture("reservations_page2")  # next_page=false

    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=page2))

    results = list(client.reservations.list_all(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31"))

    assert len(results) == 2
    assert respx_mock.calls.call_count == 1


# ---------------------------------------------------------------------------
# Specific field scenarios
# ---------------------------------------------------------------------------


def test_cancelled_reservation_has_cancelled_on(mock_client):
    """Cancelled reservation has cancelled_on populated."""
    client, respx_mock = mock_client
    fixture = load_fixture("reservations_page2")
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=fixture))

    page = client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")
    cancelled = next(r for r in page.data if r.booking_status == "cancelled")

    assert cancelled.cancelled_on == "2026-05-25"
    assert cancelled.booking_status == "cancelled"


def test_booked_reservation_cancelled_on_is_none(mock_client):
    """Booked reservations have cancelled_on=None."""
    client, respx_mock = mock_client
    fixture = load_fixture("reservations_page1")
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=fixture))

    page = client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")
    for r in page.data:
        assert r.cancelled_on is None


# ---------------------------------------------------------------------------
# Empty response
# ---------------------------------------------------------------------------


def test_empty_data_returns_empty_page(mock_client):
    """Empty data array returns a Page with an empty list."""
    client, respx_mock = mock_client
    empty = {"data": [], "next_page": False, "pms_name": None}
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=empty))

    page = client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")

    assert page.data == []
    assert page.next_page is False


def test_empty_data_list_all_yields_nothing(mock_client):
    """list_all() over an empty response yields no items."""
    client, respx_mock = mock_client
    empty = {"data": [], "next_page": False, "pms_name": None}
    respx_mock.get("/v1/reservation_data").mock(return_value=httpx.Response(200, json=empty))

    results = list(client.reservations.list_all(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31"))

    assert results == []
