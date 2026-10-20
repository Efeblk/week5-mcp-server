"""Data Explorer MCP server for Week 4.

The server wraps the REST Countries API and exposes two small, model-friendly tools
over STDIO. Start it with ``python server.py`` after installing requirements.
"""
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://restcountries.com/v3.1"
TIMEOUT_SECONDS = 10
MAX_QUERY_LENGTH = 100
SEARCH_FIELDS = "name,capital,region,population"
DETAIL_FIELDS = (
    "name,capital,region,subregion,population,currencies,languages,borders,flags,cca3"
)

mcp = FastMCP("data-explorer")


def _valid_name(value: object, label: str) -> tuple[str | None, str | None]:
    """Return a cleaned country name, or a short validation message."""
    if not isinstance(value, str):
        return None, f"{label} must be a string"

    cleaned = value.strip()
    if not cleaned:
        return None, f"{label} must not be empty"
    if len(cleaned) > MAX_QUERY_LENGTH:
        return None, f"{label} must be {MAX_QUERY_LENGTH} characters or fewer"
    return cleaned, None


def _get_json(path: str, params: dict[str, str]) -> tuple[object | None, int | None, str | None]:
    """Make one REST Countries request and turn common failures into messages."""
    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            params=params,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    except httpx.TimeoutException:
        return None, None, "upstream request timed out"
    except httpx.RequestError as exc:
        return None, None, f"upstream network error: {exc}"
    except httpx.HTTPError as exc:
        return None, None, f"upstream request failed: {exc}"

    if response.status_code == 404:
        return None, 404, None
    if response.is_error:
        return None, response.status_code, (
            f"upstream request failed with status {response.status_code}"
        )

    try:
        return response.json(), response.status_code, None
    except ValueError:
        return None, response.status_code, "upstream returned invalid JSON"


def _country_name(country: dict) -> str | None:
    """Read a country's common name without assuming every API field exists."""
    return country.get("name", {}).get("common")


@mcp.tool()
def search_countries(query: str, limit: int = 5) -> list[dict]:
    """Search country names and return name, capital, region, and population."""
    cleaned_query, error = _valid_name(query, "query")
    if error:
        return [{"error": error}]

    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        return [{"error": "limit must be an integer between 1 and 50"}]

    encoded_query = quote(cleaned_query, safe="")
    data, status_code, error = _get_json(
        f"/name/{encoded_query}", {"fields": SEARCH_FIELDS}
    )
    if status_code == 404:
        return []
    if error:
        return [{"error": error}]
    if not isinstance(data, list):
        return [{"error": "upstream returned an unexpected response"}]

    results = []
    for country in data[:limit]:
        if not isinstance(country, dict):
            continue
        results.append(
            {
                "name": _country_name(country),
                "capital": (country.get("capital") or [None])[0],
                "region": country.get("region"),
                "population": country.get("population"),
            }
        )
    return results


def _best_match(countries: list, requested_name: str) -> dict | None:
    """Prefer an exact common or official name when a broad search matches many."""
    requested = requested_name.casefold()
    for country in countries:
        if not isinstance(country, dict):
            continue
        names = country.get("name", {})
        common = str(names.get("common", "")).casefold()
        official = str(names.get("official", "")).casefold()
        if requested == common or requested == official:
            return country
    return next((country for country in countries if isinstance(country, dict)), None)


@mcp.tool()
def get_country_details(name: str) -> dict:
    """Return detailed country information for an exact name when possible."""
    cleaned_name, error = _valid_name(name, "name")
    if error:
        return {"error": error}

    encoded_name = quote(cleaned_name, safe="")
    params = {"fullText": "true", "fields": DETAIL_FIELDS}
    data, status_code, error = _get_json(f"/name/{encoded_name}", params)

    # REST Countries may not have an exact full-text match. Try its broader search once.
    if status_code == 404:
        data, status_code, error = _get_json(
            f"/name/{encoded_name}", {"fields": DETAIL_FIELDS}
        )

    if status_code == 404 or (isinstance(data, list) and not data):
        return {"error": f"no country found matching {cleaned_name!r}"}
    if error:
        return {"error": error}
    if not isinstance(data, list):
        return {"error": "upstream returned an unexpected response"}

    country = _best_match(data, cleaned_name)
    if country is None:
        return {"error": f"no country found matching {cleaned_name!r}"}

    currencies = []
    for code, currency in (country.get("currencies") or {}).items():
        currency = currency if isinstance(currency, dict) else {}
        currencies.append(
            {"code": code, "name": currency.get("name"), "symbol": currency.get("symbol")}
        )

    languages = list((country.get("languages") or {}).values())
    country_name = country.get("name") or {}
    return {
        "name": {
            "common": country_name.get("common"),
            "official": country_name.get("official"),
        },
        "capital": (country.get("capital") or [None])[0],
        "region": country.get("region"),
        "subregion": country.get("subregion"),
        "population": country.get("population"),
        "currencies": currencies,
        "languages": languages,
        "borders": country.get("borders") or [],
        "flag_url": (country.get("flags") or {}).get("png"),
    }


if __name__ == "__main__":
    mcp.run()
