"""Tests for pricelabs._http."""

from unittest import mock

import httpx
import pytest
import respx

from pricelabs._http import HTTPClient
from pricelabs._version import __version__

BASE_URL = "https://api.pricelabs.co"
API_KEY = "test-key-123"


def make_client(**kwargs) -> HTTPClient:
    """Return an HTTPClient wired to BASE_URL with a no-op sleep function."""
    kwargs.setdefault("_sleep_fn", lambda _: None)
    kwargs.setdefault("max_retries", 3)
    return HTTPClient(base_url=BASE_URL, api_key=API_KEY, **kwargs)


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------


@respx.mock
def test_get_sends_api_key_header():
    respx.get(f"{BASE_URL}/v2/test").mock(return_value=httpx.Response(200, json={}))
    make_client().get("/v2/test")
    assert respx.calls.last.request.headers["X-API-Key"] == API_KEY


@respx.mock
def test_get_sends_user_agent_header():
    respx.get(f"{BASE_URL}/v2/test").mock(return_value=httpx.Response(200, json={}))
    make_client().get("/v2/test")
    assert respx.calls.last.request.headers["User-Agent"] == f"pricelabs-python/{__version__}"


@respx.mock
def test_post_sends_headers():
    respx.post(f"{BASE_URL}/v2/listings").mock(return_value=httpx.Response(200, json={}))
    make_client().post("/v2/listings", json={"a": 1})
    req = respx.calls.last.request
    assert req.headers["X-API-Key"] == API_KEY
    assert req.headers["User-Agent"] == f"pricelabs-python/{__version__}"


@respx.mock
def test_delete_sends_headers():
    respx.delete(f"{BASE_URL}/v2/listings/1").mock(return_value=httpx.Response(200, json={}))
    make_client().delete("/v2/listings/1")
    req = respx.calls.last.request
    assert req.headers["X-API-Key"] == API_KEY


# ---------------------------------------------------------------------------
# Base URL, params, JSON body
# ---------------------------------------------------------------------------


@respx.mock
def test_base_url_is_prepended():
    route = respx.get(f"{BASE_URL}/v2/listings").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    result = make_client().get("/v2/listings")
    assert route.called
    assert result == {"items": []}


@respx.mock
def test_get_passes_params():
    respx.get(f"{BASE_URL}/v2/listings").mock(return_value=httpx.Response(200, json={}))
    make_client().get("/v2/listings", params={"page": 2, "size": 10})
    url = str(respx.calls.last.request.url)
    assert "page=2" in url
    assert "size=10" in url


@respx.mock
def test_post_sends_json_body():
    respx.post(f"{BASE_URL}/v2/listings").mock(return_value=httpx.Response(200, json={"id": 42}))
    payload = {"name": "Beach House", "nightly_rate": 150}
    make_client().post("/v2/listings", json=payload)
    import json as json_mod

    body = json_mod.loads(respx.calls.last.request.content)
    assert body == payload


# ---------------------------------------------------------------------------
# Retry: 429
# ---------------------------------------------------------------------------


@respx.mock
def test_retry_on_429():
    responses = iter([
        httpx.Response(429),
        httpx.Response(200, json={"ok": True}),
    ])
    respx.get(f"{BASE_URL}/v2/test").mock(side_effect=lambda req: next(responses))
    result = make_client(max_retries=3).get("/v2/test")
    assert result == {"ok": True}
    assert respx.calls.call_count == 2


@respx.mock
def test_retry_on_429_calls_sleep():
    sleep_fn = mock.Mock()
    responses = iter([
        httpx.Response(429),
        httpx.Response(200, json={}),
    ])
    respx.get(f"{BASE_URL}/v2/test").mock(side_effect=lambda req: next(responses))
    make_client(max_retries=3, _sleep_fn=sleep_fn).get("/v2/test")
    sleep_fn.assert_called_once()
    assert sleep_fn.call_args[0][0] >= 0


# ---------------------------------------------------------------------------
# Retry: 503
# ---------------------------------------------------------------------------


@respx.mock
def test_retry_on_503():
    responses = iter([
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(200, json={"data": "ok"}),
    ])
    respx.get(f"{BASE_URL}/v2/test").mock(side_effect=lambda req: next(responses))
    result = make_client(max_retries=3).get("/v2/test")
    assert result == {"data": "ok"}
    assert respx.calls.call_count == 3


# ---------------------------------------------------------------------------
# No retry on 401
# ---------------------------------------------------------------------------


@respx.mock
def test_no_retry_on_401():
    respx.get(f"{BASE_URL}/v2/test").mock(return_value=httpx.Response(401))
    with pytest.raises(Exception, match="HTTP 401"):
        make_client(max_retries=3).get("/v2/test")
    assert respx.calls.call_count == 1


# ---------------------------------------------------------------------------
# POST retryable flag
# ---------------------------------------------------------------------------


@respx.mock
def test_post_retryable_false_does_not_retry_on_429():
    respx.post(f"{BASE_URL}/v2/listings").mock(return_value=httpx.Response(429))
    with pytest.raises(Exception, match="HTTP 429"):
        make_client(max_retries=3).post("/v2/listings", retryable=False)
    assert respx.calls.call_count == 1


@respx.mock
def test_post_retryable_true_retries_on_429():
    responses = iter([
        httpx.Response(429),
        httpx.Response(200, json={"created": True}),
    ])
    respx.post(f"{BASE_URL}/v2/listings").mock(side_effect=lambda req: next(responses))
    result = make_client(max_retries=3).post("/v2/listings", retryable=True)
    assert result == {"created": True}
    assert respx.calls.call_count == 2


# ---------------------------------------------------------------------------
# Retry-After header
# ---------------------------------------------------------------------------


@respx.mock
def test_retry_after_header_is_respected():
    sleep_fn = mock.Mock()
    responses = iter([
        httpx.Response(429, headers={"Retry-After": "5"}),
        httpx.Response(200, json={}),
    ])
    respx.get(f"{BASE_URL}/v2/test").mock(side_effect=lambda req: next(responses))
    make_client(max_retries=3, _sleep_fn=sleep_fn).get("/v2/test")
    assert sleep_fn.call_count >= 1
    sleep_duration = sleep_fn.call_args_list[0][0][0]
    assert sleep_duration >= 5.0


# ---------------------------------------------------------------------------
# DELETE 204
# ---------------------------------------------------------------------------


@respx.mock
def test_delete_204_returns_none():
    respx.delete(f"{BASE_URL}/v2/listings/7").mock(return_value=httpx.Response(204))
    result = make_client().delete("/v2/listings/7")
    assert result is None


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


def test_close_closes_httpx_client():
    client = make_client()
    with mock.patch.object(client._client, "close") as mock_close:
        client.close()
    mock_close.assert_called_once()


# ---------------------------------------------------------------------------
# Retry-After fallback and retry exhaustion
# ---------------------------------------------------------------------------


@respx.mock
def test_retry_after_invalid_value_falls_back_to_jitter():
    """Malformed Retry-After header exercises the ValueError/TypeError branch."""
    sleep_fn = mock.Mock()
    responses = iter([
        httpx.Response(429, headers={"Retry-After": "not-a-number"}),
        httpx.Response(200, json={"ok": True}),
    ])
    respx.get(f"{BASE_URL}/v2/test").mock(side_effect=lambda req: next(responses))
    result = make_client(max_retries=3, _sleep_fn=sleep_fn).get("/v2/test")
    assert result == {"ok": True}
    sleep_fn.assert_called_once()


@respx.mock
def test_retries_exhausted_raises():
    """When all retries return 429, the final error is raised."""
    respx.get(f"{BASE_URL}/v2/test").mock(return_value=httpx.Response(429))
    with pytest.raises(Exception, match="HTTP 429"):
        make_client(max_retries=2).get("/v2/test")
    assert respx.calls.call_count == 2
