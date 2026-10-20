"""Tests for the Data Explorer tools without calling the real API by default."""
import os

import httpx
import pytest

import server

JAPAN = {
    "names": {"common": "Japan", "official": "Japan"},
    "capitals": [{"name": "Tokyo", "attributes": {"primary": True}}],
    "region": "Asia",
    "subregion": "Eastern Asia",
    "population": 123000000,
    "currencies": [{"code": "JPY", "name": "Japanese yen", "symbol": "¥"}],
    "languages": [{"name": "Japanese", "iso639_1": "ja"}],
    "borders": [],
    "flag": {"url_png": "https://flags.restcountries.com/v5/w640/jp.png"},
}


def response(status_code: int, json_data=None, text: str = "") -> httpx.Response:
    """Build an httpx response that behaves like a real request response."""
    request = httpx.Request("GET", f"{server.BASE_URL}/name")
    if json_data is not None:
        return httpx.Response(status_code, json=json_data, request=request)
    return httpx.Response(status_code, text=text, request=request)


def objects(*countries) -> dict:
    """Wrap countries in the v5 success envelope."""
    return {"data": {"objects": list(countries), "meta": {"total": len(countries)}}}


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("RESTCOUNTRIES_API_KEY", "test-key")


def test_search_success_sends_query_and_key(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response(200, objects(JAPAN))

    monkeypatch.setattr(server.httpx, "get", fake_get)

    assert server.search_countries("  japan ") == [
        {"name": "Japan", "capital": "Tokyo", "region": "Asia", "population": 123000000}
    ]
    url, kwargs = calls[0]
    assert url == f"{server.BASE_URL}/name"
    assert kwargs["params"] == {"q": "japan", "limit": 5, "response_fields": server.SEARCH_FIELDS}
    assert kwargs["headers"] == {"Authorization": "Bearer test-key"}


def test_details_success_picks_exact_match(monkeypatch):
    nigeria = {**JAPAN, "names": {"common": "Nigeria", "official": "Federal Republic of Nigeria"}}
    niger = {**JAPAN, "names": {"common": "Niger", "official": "Republic of Niger"}}
    monkeypatch.setattr(
        server.httpx, "get", lambda *a, **k: response(200, objects(nigeria, niger))
    )

    assert server.get_country_details("niger")["name"]["common"] == "Niger"


def test_details_return_shape(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *a, **k: response(200, objects(JAPAN)))

    assert server.get_country_details("Japan") == {
        "name": {"common": "Japan", "official": "Japan"},
        "capital": "Tokyo",
        "region": "Asia",
        "subregion": "Eastern Asia",
        "population": 123000000,
        "currencies": [{"code": "JPY", "name": "Japanese yen", "symbol": "¥"}],
        "languages": ["Japanese"],
        "borders": [],
        "flag_url": "https://flags.restcountries.com/v5/w640/jp.png",
    }


def test_empty_input_returns_clean_errors():
    assert server.search_countries("   ") == [{"error": "query must not be empty"}]
    assert server.get_country_details("") == {"error": "name must not be empty"}
    assert server.get_country_details(None) == {"error": "name must be a string"}
    assert server.get_country_details("x" * 101) == {
        "error": "name must be 100 characters or fewer"
    }


def test_no_results(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *a, **k: response(200, objects()))
    assert server.search_countries("atlantis") == []
    assert server.get_country_details("atlantis") == {
        "error": "no country found matching 'atlantis'"
    }


def test_404_is_treated_as_no_results(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *a, **k: response(404))
    assert server.search_countries("atlantis") == []


def test_missing_api_key_does_not_make_a_request(monkeypatch):
    monkeypatch.delenv("RESTCOUNTRIES_API_KEY")

    def should_not_run(*args, **kwargs):
        raise AssertionError("no request should be made without a key")

    monkeypatch.setattr(server.httpx, "get", should_not_run)
    assert "RESTCOUNTRIES_API_KEY is not set" in server.get_country_details("japan")["error"]


def test_rejected_api_key(monkeypatch):
    body = {"errors": [{"message": "No matching authorization key found."}]}
    monkeypatch.setattr(server.httpx, "get", lambda *a, **k: response(401, body))
    assert server.search_countries("japan") == [
        {"error": "API key was rejected (status 401): No matching authorization key found."}
    ]


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *a, **k: response(429))
    assert server.get_country_details("japan") == {
        "error": "API rate limit reached, try again later"
    }


def test_timeout_returns_clean_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(server.httpx, "get", fake_get)
    assert server.search_countries("germany") == [{"error": "upstream request timed out"}]


def test_network_error_returns_clean_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("no internet")

    monkeypatch.setattr(server.httpx, "get", fake_get)
    assert server.get_country_details("japan") == {
        "error": "upstream network error: no internet"
    }


def test_500_returns_status_code_in_error(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *a, **k: response(500))
    assert server.get_country_details("japan") == {
        "error": "upstream request failed with status 500"
    }


@pytest.mark.parametrize("body", ["<html>not json</html>", '{"unexpected": true}'])
def test_unexpected_body_returns_clean_error(monkeypatch, body):
    monkeypatch.setattr(server.httpx, "get", lambda *a, **k: response(200, text=body))
    assert server.search_countries("japan") == [
        {"error": "upstream returned an unexpected response"}
    ]


@pytest.mark.parametrize("limit", [0, 51, "5", True])
def test_bad_limit_does_not_make_a_request(monkeypatch, limit):
    def should_not_run(*args, **kwargs):
        raise AssertionError("invalid limit should be rejected before the request")

    monkeypatch.setattr(server.httpx, "get", should_not_run)
    assert server.search_countries("germany", limit=limit) == [
        {"error": "limit must be an integer between 1 and 50"}
    ]


@pytest.mark.skipif(os.getenv("LIVE") != "1", reason="set LIVE=1 to call REST Countries")
def test_live_details(monkeypatch):
    monkeypatch.undo()  # use the real RESTCOUNTRIES_API_KEY, not the fixture's fake key
    result = server.get_country_details("germany")
    assert result["name"]["common"] == "Germany"
    assert "FRA" in result["borders"]
