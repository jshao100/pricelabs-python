"""Tests for the PriceLabs neighborhood/market data models and Market namespace."""

import httpx

from pricelabs.market import (
    BedroomCategory,
    DataSection,
    Market,
    NeighborhoodData,
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

    def test_parse_with_category_and_labels(self):
        """Category dict and Labels list parse correctly."""
        raw = {
            "Category": {
                "1": {
                    "X_values": ["2026-06-01"],
                    "Y_values": [[100]],
                    "Listings Used": 5,
                    "Active Used": 4,
                    "Inactive Used": 1,
                },
            },
            "Labels": ["50th Percentile"],
        }
        section = DataSection.model_validate(raw)
        assert "1" in section.category
        assert section.labels == ["50th Percentile"]
        assert section.category["1"].x_values == ["2026-06-01"]

    def test_multiple_bedroom_keys(self):
        """Multiple bedroom categories are all extracted from the fixture."""
        raw = _fixture()["Future Percentile Prices"]
        section = DataSection.model_validate(raw)
        assert set(section.category.keys()) == {"2", "3", "4"}

    def test_empty_defaults(self):
        """Category and Labels default to empty when not provided."""
        section = DataSection.model_validate({})
        assert section.category == {}
        assert section.labels == []


class TestOccupancySection:
    """Tests for Future Occ/New/Canc as DataSection."""

    def test_parse_as_data_section(self):
        """Future Occ/New/Canc parses as a DataSection with bedroom categories."""
        raw = _fixture()["Future Occ/New/Canc"]
        section = DataSection.model_validate(raw)
        assert len(section.labels) > 0
        assert len(section.category) > 0
        assert set(section.category.keys()) == {"2", "3", "4"}


class TestMarketKPISection:
    """Tests for Market KPI as DataSection."""

    def test_parse_as_data_section(self):
        """Market KPI parses as a DataSection with bedroom categories."""
        raw = _fixture()["Market KPI"]
        section = DataSection.model_validate(raw)
        assert isinstance(section.category, dict)
        assert set(section.category.keys()) == {"2", "3", "4"}

    def test_market_kpi_labels(self):
        """Market KPI labels include expected metric names."""
        raw = _fixture()["Market KPI"]
        section = DataSection.model_validate(raw)
        assert "Revenue" in section.labels
        assert "LOS" in section.labels
        assert "Booking Window" in section.labels


class TestNeighborhoodData:
    """Tests for the top-level NeighborhoodData model."""

    def test_parse_full_response(self):
        """Full fixture parses into NeighborhoodData without errors."""
        data = _fixture()
        nd = NeighborhoodData.model_validate(data)
        assert nd.listings_used == 350
        assert nd.currency == "USD"
        assert nd.lat == 39.8072
        assert nd.lng == -86.1647
        assert nd.source == "airbnb"
        assert nd.neighborhood_data_source == "Nearby Listings"

    def test_nested_access(self):
        """Drill into nested bedroom category data."""
        nd = NeighborhoodData.model_validate(_fixture())
        cat3 = nd.future_percentile_prices.category["3"]
        assert len(cat3.x_values) == 360
        assert cat3.x_values[0] == "2026-05-31"
        assert cat3.listings_used == 160
        assert cat3.active_used == 160

    def test_bedroom_category_keys(self):
        """Bedroom categories include 2, 3, and 4 bedroom types."""
        nd = NeighborhoodData.model_validate(_fixture())
        keys = set(nd.future_percentile_prices.category.keys())
        assert "2" in keys
        assert "3" in keys
        assert "4" in keys

    def test_labels_values(self):
        """Labels arrays contain the expected percentile/metric names."""
        nd = NeighborhoodData.model_validate(_fixture())
        assert "25th Percentile" in nd.future_percentile_prices.labels
        assert "50th Percentile" in nd.future_percentile_prices.labels
        assert "75th Percentile" in nd.future_percentile_prices.labels
        assert "Occupancy" in nd.future_occupancy.labels
        assert "New Bookings" in nd.future_occupancy.labels

    def test_market_kpi_present(self):
        """Market KPI is parsed when present in the response."""
        nd = NeighborhoodData.model_validate(_fixture())
        assert nd.market_kpi is not None

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
            if isinstance(cat.y_values, list):
                assert len(cat.y_values) == len(prices.labels), (
                    f"Category {key}: y_values has {len(cat.y_values)} rows "
                    f"but labels has {len(prices.labels)} entries"
                )

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
        assert "2" in summary.category
        assert "3" in summary.category
        assert "4" in summary.category
        assert "All" in summary.category
        assert len(summary.labels) == 4

    def test_future_percentile_prices_monthly_in_extras(self):
        """Future Percentile Prices Monthly is captured as extra field."""
        data = _fixture()
        nd = NeighborhoodData.model_validate(data)
        assert "Future Percentile Prices Monthly" in nd.model_extra


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
        assert result.listings_used == 350
        assert result.currency == "USD"
        assert result.market_kpi is not None
        assert len(result.market_kpi.category) == 3

    def test_client_market_property_returns_market_instance(self, mock_client):
        """client.market returns a Market instance."""
        client, _ = mock_client
        assert isinstance(client.market, Market)
