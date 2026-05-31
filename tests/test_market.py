"""Tests for the PriceLabs neighborhood/market data models and Market namespace."""

import httpx

from pricelabs.market import (
    BedroomCategory,
    DataSection,
    Market,
    MarketKPI,
    NeighborhoodData,
    OccupancyData,
)
from tests.conftest import load_fixture

BASE_URL = "https://api.pricelabs.co"
LISTING_ID = "listing-abc"
PMS = "airbnb"
NEIGHBORHOOD_PATH = "/v1/neighborhood_data"


def _fixture() -> dict:
    return load_fixture("neighborhood_data")


class TestBedroomCategory:
    """Tests for BedroomCategory model."""

    def test_parse_with_aliases(self):
        """Parse bedroom category data using API field names."""
        raw = {
            "X_values": ["2026-06-01", "2026-06-08"],
            "Y_values": [[100, 120], [110, 130]],
            "Listings Used": 10,
            "Active Used": 8,
            "Inactive Used": 2,
        }
        cat = BedroomCategory.model_validate(raw)
        assert cat.x_values == ["2026-06-01", "2026-06-08"]
        assert cat.y_values == [[100, 120], [110, 130]]
        assert cat.listings_used == 10
        assert cat.active_used == 8
        assert cat.inactive_used == 2

    def test_optional_fields_default_none(self):
        """Listings/active/inactive fields default to None when absent."""
        raw = {
            "X_values": ["2026-06-01"],
            "Y_values": [[50]],
        }
        cat = BedroomCategory.model_validate(raw)
        assert cat.listings_used is None
        assert cat.active_used is None
        assert cat.inactive_used is None


class TestDataSection:
    """Tests for DataSection model."""

    def test_extracts_categories_from_flat_dict(self):
        """Bedroom keys are separated from Labels into the category dict."""
        raw = {
            "1": {
                "X_values": ["2026-06-01"],
                "Y_values": [[100]],
                "Listings Used": 5,
                "Active Used": 4,
                "Inactive Used": 1,
            },
            "Labels": ["p50"],
        }
        section = DataSection.model_validate(raw)
        assert "1" in section.category
        assert section.labels == ["p50"]
        assert section.category["1"].x_values == ["2026-06-01"]

    def test_multiple_bedroom_keys(self):
        """Multiple bedroom categories are all extracted."""
        raw = _fixture()["Future Percentile Prices"]
        section = DataSection.model_validate(raw)
        assert set(section.category.keys()) == {"-1", "0", "1", "2"}

    def test_validator_passthrough_for_non_dict(self):
        """The model_validator returns non-dict input unchanged (Pydantic handles the error)."""
        result = DataSection._extract_categories("not-a-dict")
        assert result == "not-a-dict"


class TestOccupancyData:
    """Tests for OccupancyData model."""

    def test_parse_flat_structure(self):
        """OccupancyData parses the flat Future Occ/New/Canc structure."""
        raw = _fixture()["Future Occ/New/Canc"]
        occ = OccupancyData.model_validate(raw)
        assert len(occ.x_values) == 5
        assert len(occ.y_values) == 6
        assert len(occ.labels) == 6


class TestMarketKPI:
    """Tests for MarketKPI model."""

    def test_parse_kpi(self):
        """MarketKPI parses all expected fields."""
        raw = _fixture()["Market KPI"]
        kpi = MarketKPI.model_validate(raw)
        assert kpi.avg_daily_rate == 185.50
        assert kpi.occupancy_rate == 72.5
        assert kpi.total_active_listings == 42

    def test_extra_fields_allowed(self):
        """Unknown fields are preserved via extra='allow'."""
        raw = {"avg_daily_rate": 100, "revenue_per_available_night": 80,
               "occupancy_rate": 70, "avg_booking_lead_time_days": 10,
               "avg_length_of_stay_days": 2.5, "total_active_listings": 30,
               "new_metric": 42}
        kpi = MarketKPI.model_validate(raw)
        assert kpi.model_extra["new_metric"] == 42


class TestNeighborhoodData:
    """Tests for the top-level NeighborhoodData model."""

    def test_parse_full_response(self):
        """Full fixture parses into NeighborhoodData without errors."""
        data = _fixture()
        nd = NeighborhoodData.model_validate(data)
        assert nd.listings_used == 42
        assert nd.currency == "USD"
        assert nd.lat == 37.7749
        assert nd.lng == -122.4194
        assert nd.source == "pricelabs"
        assert nd.neighborhood_data_source == "San Francisco, CA - Downtown"

    def test_nested_access(self):
        """Drill into nested bedroom category data."""
        nd = NeighborhoodData.model_validate(_fixture())
        cat1 = nd.future_percentile_prices.category["1"]
        assert cat1.x_values == [
            "2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29",
        ]
        assert cat1.listings_used == 18
        assert cat1.active_used == 15

    def test_bedroom_category_keys(self):
        """Bedroom categories include room (-1), studio (0), and numbered bedrooms."""
        nd = NeighborhoodData.model_validate(_fixture())
        keys = set(nd.future_percentile_prices.category.keys())
        assert "-1" in keys
        assert "0" in keys
        assert "1" in keys
        assert "2" in keys

    def test_labels_values(self):
        """Labels arrays contain the expected percentile/metric names."""
        nd = NeighborhoodData.model_validate(_fixture())
        assert nd.future_percentile_prices.labels == [
            "10th percentile", "25th percentile", "50th percentile",
            "75th percentile", "90th percentile",
        ]
        assert "Occupancy %" in nd.future_occupancy.labels
        assert "New Bookings %" in nd.future_occupancy.labels

    def test_market_kpi_present(self):
        """Market KPI is parsed when present in the response."""
        nd = NeighborhoodData.model_validate(_fixture())
        assert nd.market_kpi is not None
        assert nd.market_kpi.avg_daily_rate == 185.50

    def test_market_kpi_absent(self):
        """Market KPI defaults to None when missing from the response."""
        data = _fixture()
        del data["Market KPI"]
        nd = NeighborhoodData.model_validate(data)
        assert nd.market_kpi is None

    def test_y_values_shape_matches_labels(self):
        """Each section's y_values row count matches its labels count."""
        nd = NeighborhoodData.model_validate(_fixture())

        prices = nd.future_percentile_prices
        for key, cat in prices.category.items():
            assert len(cat.y_values) == len(prices.labels), (
                f"Category {key}: y_values has {len(cat.y_values)} rows "
                f"but labels has {len(prices.labels)} entries"
            )

        occ = nd.future_occupancy
        assert len(occ.y_values) == len(occ.labels)

    def test_extra_top_level_fields_allowed(self):
        """Unknown top-level fields are preserved via extra='allow'."""
        data = _fixture()
        data["New Section"] = {"foo": "bar"}
        nd = NeighborhoodData.model_validate(data)
        assert nd.model_extra["New Section"] == {"foo": "bar"}

    def test_string_lat_lng_coerced(self):
        """String lat/lng values (as documented in some API versions) are coerced to float."""
        data = _fixture()
        data["lat"] = "27.89"
        data["lng"] = "-82.78"
        nd = NeighborhoodData.model_validate(data)
        assert nd.lat == 27.89
        assert nd.lng == -82.78

    def test_summary_table_base_price(self):
        """Summary Table Base Price section parses correctly."""
        nd = NeighborhoodData.model_validate(_fixture())
        summary = nd.summary_table_base_price
        assert "1" in summary.category
        assert "2" in summary.category
        assert len(summary.labels) == 5


class TestMarketNamespace:
    """Tests for the Market namespace class."""

    def test_neighborhood_sends_correct_get(self, mock_client):
        """neighborhood() sends GET to /v1/neighborhood_data with pms and listing_id params."""
        client, respx_mock = mock_client
        fixture = load_fixture("neighborhood_data")
        respx_mock.get(f"{BASE_URL}{NEIGHBORHOOD_PATH}").mock(
            return_value=httpx.Response(200, json={"data": fixture})
        )

        client.market.neighborhood(LISTING_ID, PMS)

        req = respx_mock.calls.last.request
        assert req.method == "GET"
        assert f"pms={PMS}" in str(req.url)
        assert f"listing_id={LISTING_ID}" in str(req.url)

    def test_neighborhood_parses_into_neighborhood_data(self, mock_client):
        """neighborhood() parses the response data envelope into NeighborhoodData."""
        client, respx_mock = mock_client
        fixture = load_fixture("neighborhood_data")
        respx_mock.get(f"{BASE_URL}{NEIGHBORHOOD_PATH}").mock(
            return_value=httpx.Response(200, json={"data": fixture})
        )

        result = client.market.neighborhood(LISTING_ID, PMS)

        assert isinstance(result, NeighborhoodData)
        assert result.listings_used == 42
        assert result.currency == "USD"
        assert result.market_kpi is not None
        assert result.market_kpi.avg_daily_rate == 185.50

    def test_client_market_property_returns_market_instance(self, mock_client):
        """client.market returns a Market instance."""
        client, _ = mock_client
        assert isinstance(client.market, Market)
