"""Shared test fixtures and helpers for the PriceLabs SDK test suite."""

import json
import logging
from pathlib import Path
from typing import Generator

import pytest
import respx

from pricelabs import PriceLabsClient

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file by name (without .json extension).

    Args:
        name: Fixture filename without the ``.json`` suffix.

    Returns:
        Parsed JSON content as a dict.

    Raises:
        FileNotFoundError: If the fixture file does not exist.
    """
    path = FIXTURES_DIR / f"{name}.json"
    logger.debug("Loading fixture: %s", path)
    return json.loads(path.read_text())


@pytest.fixture
def mock_api_key() -> str:
    """Return a stable fake API key for use in tests."""
    return "test_api_key_12345"


@pytest.fixture
def mock_client(
    mock_api_key: str, monkeypatch: pytest.MonkeyPatch
) -> Generator[tuple[PriceLabsClient, respx.MockRouter], None, None]:
    """Create a PriceLabsClient with mocked HTTP transport.

    Yields:
        A ``(client, respx_mock)`` tuple. Use ``respx_mock`` to register routes
        and ``client`` to call SDK methods under test.
    """
    monkeypatch.delenv("PRICELABS_API_KEY", raising=False)
    monkeypatch.delenv("PRICELABS_BASE_URL", raising=False)
    with respx.mock(base_url="https://api.pricelabs.co") as respx_mock:
        client = PriceLabsClient(api_key=mock_api_key)
        logger.info("mock_client fixture: client created")
        yield client, respx_mock
        client.close()
