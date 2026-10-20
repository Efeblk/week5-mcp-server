"""Tests for the Data Explorer tools without calling the public API by default."""
import os

import httpx
import pytest

import server


def response(status_code: int, json_data=None, text: str = "") -> httpx.Response:
    """Build an httpx response that behaves like a real request response."""
    request = httpx.Request("GET", "https://restcountries.com/v3.1/name/test")
    if json_data is not None:
        return httpx.Response(status_code, json=json_data, request=request)
    return httpx.Response(status_code, text=text, request=request)


def test_search_success_and_url_encoding(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response(
            200,
            [{"name": {"common": "United States"}, "capital": ["Washington, D.C."],
              "region": "Americas", "population": 340000000}],
        )

    monkeypatch.setattr(server.httpx, "get", fake_get)

    assert server.search_countries("united states") == [
        {"name": "United States", "capital": "Washington, D.C.",
         "region": "Americas", "population": 340000000}
    ]
    assert calls[0][0].endswith("/name/united%20states")
    assert calls[0][1]["params"]["fields"] == server.SEARCH_FIELDS


def test_details_success_and_full_text_fallback(monkeypatch):
    calls = []
    country = {
        "name": {"common": "Japan", "official": "Japan"},
        "capital": ["Tokyo"], "region": "Asia", "subregion": "Eastern Asia",
        "population": 123000000,
        "currencies": {"JPY": {"name": "Japanese yen", "symbol": "¥"}},
        "languages": {"jpn": "Japanese"}, "borders": [],
        "flags": {"png": "https://example.test/japan.png"},
    }

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response(404) if len(calls) == 1 else response(200, [country])

    monkeypatch.setattr(server.httpx, "get", fake_get)

    result = server.get_country_details("Japan")
    assert result["name"] == {"common": "Japan", "official": "Japan"}
    assert result["currencies"] == [
        {"code": "JPY", "name": "Japanese yen", "symbol": "¥"}
    ]
    assert result["languages"] == ["Japanese"]
    assert result["flag_url"] == "https://example.test/japan.png"
    assert len(calls) == 2
    assert calls[0][1]["params"]["fullText"] == "true"
    assert "fullText" not in calls[1][1]["params"]


def test_empty_input_returns_clean_errors():
    assert server.search_countries("   ") == [{"error": "query must not be empty"}]
    assert server.get_country_details("") == {"error": "name must not be empty"}


def test_search_404_is_an_empty_list(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: response(404))
    assert server.search_countries("atlantis") == []


def test_details_404_after_fallback_is_no_match(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: response(404))
    assert server.get_country_details("atlantis") == {
        "error": "no country found matching 'atlantis'"
    }


def test_timeout_returns_clean_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(server.httpx, "get", fake_get)
    assert server.search_countries("germany") == [
        {"error": "upstream request timed out"}
    ]


def test_500_returns_status_code_in_error(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: response(500))
    assert server.get_country_details("japan") == {
        "error": "upstream request failed with status 500"
    }


@pytest.mark.parametrize("limit", [0, 51, "5", True])
def test_bad_limit_does_not_make_a_request(monkeypatch, limit):
    def should_not_run(*args, **kwargs):
        raise AssertionError("invalid limit should be rejected before the request")

    monkeypatch.setattr(server.httpx, "get", should_not_run)
    assert server.search_countries("germany", limit=limit) == [
        {"error": "limit must be an integer between 1 and 50"}
    ]


@pytest.mark.skipif(os.getenv("LIVE") != "1", reason="set LIVE=1 to call REST Countries")
def test_live_search_returns_a_result():
    results = server.search_countries("germany")
    assert results and results[0]["name"] == "Germany"
