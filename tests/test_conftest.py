"""Tests for shared conftest fixtures and helpers."""

import pytest

from pricelabs import PriceLabsClient
from pricelabs._http import HTTPClient
from tests.conftest import load_fixture


def test_load_fixture_raises_for_missing_fixture():
    """load_fixture raises FileNotFoundError when the fixture file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_fixture("does_not_exist")


def test_mock_api_key_returns_string(mock_api_key: str):
    """mock_api_key fixture returns a non-empty string."""
    assert isinstance(mock_api_key, str)
    assert len(mock_api_key) > 0


def test_mock_client_has_http_attribute(mock_client):
    """mock_client fixture yields a PriceLabsClient with an _http attribute."""
    client, _respx_mock = mock_client
    assert isinstance(client, PriceLabsClient)
    assert hasattr(client, "_http")
    assert isinstance(client._http, HTTPClient)
