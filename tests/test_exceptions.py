"""Tests for pricelabs.exceptions."""

from __future__ import annotations

import httpx
import pytest

from pricelabs.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    ForbiddenError,
    InvalidRequestError,
    NetworkError,
    NotFoundError,
    PriceLabsError,
    RateLimitError,
    ServerError,
    raise_for_status,
)

# ---------------------------------------------------------------------------
# Hierarchy checks
# ---------------------------------------------------------------------------


def test_api_error_is_pricelabs_error():
    assert issubclass(APIError, PriceLabsError)


def test_authentication_error_is_pricelabs_error():
    assert issubclass(AuthenticationError, PriceLabsError)


def test_forbidden_error_is_pricelabs_error():
    assert issubclass(ForbiddenError, PriceLabsError)


def test_not_found_error_is_pricelabs_error():
    assert issubclass(NotFoundError, PriceLabsError)


def test_invalid_request_error_is_pricelabs_error():
    assert issubclass(InvalidRequestError, PriceLabsError)


def test_rate_limit_error_is_pricelabs_error():
    assert issubclass(RateLimitError, PriceLabsError)


def test_server_error_is_pricelabs_error():
    assert issubclass(ServerError, PriceLabsError)


def test_configuration_error_is_pricelabs_error():
    assert issubclass(ConfigurationError, PriceLabsError)


def test_network_error_is_pricelabs_error():
    assert issubclass(NetworkError, PriceLabsError)


# ---------------------------------------------------------------------------
# APIError attributes
# ---------------------------------------------------------------------------


def test_api_error_attributes():
    raw = {"error": "bad request"}
    err = APIError("bad request", 400, raw)
    assert str(err) == "bad request"
    assert err.status_code == 400
    assert err.raw == raw


def test_api_error_raw_defaults_to_none():
    err = APIError("oops", 400)
    assert err.raw is None


# ---------------------------------------------------------------------------
# RateLimitError attributes
# ---------------------------------------------------------------------------


def test_rate_limit_error_retry_after():
    err = RateLimitError("slow down", retry_after=30)
    assert err.retry_after == 30
    assert err.status_code == 429


def test_rate_limit_error_retry_after_defaults_to_none():
    err = RateLimitError("slow down")
    assert err.retry_after is None


# ---------------------------------------------------------------------------
# raise_for_status — success cases (should not raise)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status_code", [200, 201, 204])
def test_raise_for_status_ok(status_code):
    response = httpx.Response(status_code)
    raise_for_status(response)  # must not raise


# ---------------------------------------------------------------------------
# raise_for_status — mapped error codes
# ---------------------------------------------------------------------------


def _make_json_response(
    status_code: int, body: dict, headers: dict | None = None
) -> httpx.Response:
    return httpx.Response(status_code, json=body, headers=headers or {})


def test_raise_for_status_401():
    response = _make_json_response(401, {"error": "unauthorized"})
    with pytest.raises(AuthenticationError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 401
    assert "unauthorized" in str(exc_info.value)


def test_raise_for_status_403():
    response = _make_json_response(403, {"error": "forbidden"})
    with pytest.raises(ForbiddenError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 403


def test_raise_for_status_404():
    response = _make_json_response(404, {"message": "not found"})
    with pytest.raises(NotFoundError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value)


def test_raise_for_status_422():
    response = _make_json_response(422, {"error": "invalid"})
    with pytest.raises(InvalidRequestError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 422


def test_raise_for_status_429():
    response = _make_json_response(429, {"error": "rate limited"})
    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after is None


def test_raise_for_status_429_with_retry_after():
    response = _make_json_response(429, {"error": "rate limited"}, headers={"Retry-After": "60"})
    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.retry_after == 60


def test_raise_for_status_429_with_invalid_retry_after():
    response = _make_json_response(429, {"error": "rate limited"}, headers={"Retry-After": "soon"})
    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.retry_after is None


def test_raise_for_status_500():
    response = _make_json_response(500, {"error": "internal server error"})
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 500


def test_raise_for_status_502():
    response = httpx.Response(502)
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 502


def test_raise_for_status_503():
    response = _make_json_response(503, {"message": "service unavailable"})
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 503


def test_raise_for_status_other_4xx():
    response = _make_json_response(409, {"error": "conflict"})
    with pytest.raises(APIError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 409
    assert not isinstance(exc_info.value, AuthenticationError)


# ---------------------------------------------------------------------------
# raise_for_status — non-JSON body
# ---------------------------------------------------------------------------


def test_raise_for_status_non_json_body():
    response = httpx.Response(
        500, content=b"Internal Server Error", headers={"content-type": "text/plain"}
    )
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(response)
    # message falls back to status code string
    assert str(exc_info.value) == "500"
    assert exc_info.value.raw is None


def test_raise_for_status_empty_body():
    response = httpx.Response(401)
    with pytest.raises(AuthenticationError) as exc_info:
        raise_for_status(response)
    assert exc_info.value.status_code == 401
