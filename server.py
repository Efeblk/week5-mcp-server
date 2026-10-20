"""Data Explorer MCP server for Week 4.

The server wraps the REST Countries API and exposes two small, model-friendly tools
over STDIO. Start it with ``python server.py`` after installing requirements.

REST Countries retired its old no-key endpoints (v1-v4) in 2026. The current v5 API
needs a free API key from https://restcountries.com/sign-up, which this server reads
from the RESTCOUNTRIES_API_KEY environment variable.
"""
import os

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.restcountries.com/countries/v5"
TIMEOUT_SECONDS = 10
MAX_QUERY_LENGTH = 100
MAX_LIMIT = 50
SEARCH_FIELDS = "names.common,capitals,region,population"
DETAIL_FIELDS = (
    "names.common,names.official,capitals,region,subregion,population,"
    "currencies,languages,borders,flag.url_png"
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


def _upstream_message(response: httpx.Response) -> str:
    """Read the API's own error message ({"errors": [{"message": ...}]}) if present."""
    try:
        return response.json()["errors"][0]["message"]
    except (ValueError, KeyError, IndexError, TypeError):
        return ""


def _search_by_name(query: str, limit: int, fields: str) -> tuple[list | None, str | None]:
    """Search countries by name and turn every kind of failure into a message.

    Returns (countries, None) on success, or (None, error message) on failure.
    """
    api_key = os.getenv("RESTCOUNTRIES_API_KEY", "").strip()
    if not api_key:
        return None, "RESTCOUNTRIES_API_KEY is not set (get a free key at https://restcountries.com/sign-up)"

    try:
        response = httpx.get(
            f"{BASE_URL}/name",
            params={"q": query, "limit": limit, "response_fields": fields},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        return None, "upstream request timed out"
    except httpx.HTTPError as exc:
        return None, f"upstream network error: {exc}"

    if response.status_code == 404:
        return [], None  # no matches is not an error
    if response.status_code in (401, 403):
        return None, f"API key was rejected (status {response.status_code}): {_upstream_message(response)}"
    if response.status_code == 429:
        return None, "API rate limit reached, try again later"
    if response.is_error:
        return None, f"upstream request failed with status {response.status_code}"

    try:
        countries = response.json()["data"]["objects"]
    except (ValueError, KeyError, TypeError):
        return None, "upstream returned an unexpected response"
    if not isinstance(countries, list):
        return None, "upstream returned an unexpected response"
    return [c for c in countries if isinstance(c, dict)], None


def _capital(country: dict) -> str | None:
    """v5 returns capitals as a list of objects; prefer the primary one."""
    capitals = [c for c in country.get("capitals") or [] if isinstance(c, dict)]
    for capital in capitals:
        if (capital.get("attributes") or {}).get("primary"):
            return capital.get("name")
    return capitals[0].get("name") if capitals else None


@mcp.tool()
def search_countries(query: str, limit: int = 5) -> list[dict]:
    """Search countries by name. Returns a list of {name, capital, region, population}.

    An empty list means nothing matched. A single {"error": ...} item means the input
    was invalid or the API call failed.
    """
    cleaned_query, error = _valid_name(query, "query")
    if error:
        return [{"error": error}]

    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_LIMIT:
        return [{"error": f"limit must be an integer between 1 and {MAX_LIMIT}"}]

    countries, error = _search_by_name(cleaned_query, limit, SEARCH_FIELDS)
    if error:
        return [{"error": error}]

    return [
        {
            "name": (c.get("names") or {}).get("common"),
            "capital": _capital(c),
            "region": c.get("region"),
            "population": c.get("population"),
        }
        for c in countries[:limit]
    ]


def _best_match(countries: list[dict], requested_name: str) -> dict | None:
    """Prefer an exact common or official name when a substring search matches many."""
    requested = requested_name.casefold()
    for country in countries:
        names = country.get("names") or {}
        if requested in (
            str(names.get("common", "")).casefold(),
            str(names.get("official", "")).casefold(),
        ):
            return country
    return countries[0] if countries else None


@mcp.tool()
def get_country_details(name: str) -> dict:
    """Get one country's details: currencies, languages, borders, and flag URL.

    Returns {"error": ...} if the name is invalid, nothing matches, or the API call fails.
    """
    cleaned_name, error = _valid_name(name, "name")
    if error:
        return {"error": error}

    # The name search is a substring match ("niger" also finds "Nigeria"), so ask for
    # several results and pick the exact name if it is among them.
    countries, error = _search_by_name(cleaned_name, 25, DETAIL_FIELDS)
    if error:
        return {"error": error}

    country = _best_match(countries, cleaned_name)
    if country is None:
        return {"error": f"no country found matching {cleaned_name!r}"}

    names = country.get("names") or {}
    return {
        "name": {"common": names.get("common"), "official": names.get("official")},
        "capital": _capital(country),
        "region": country.get("region"),
        "subregion": country.get("subregion"),
        "population": country.get("population"),
        "currencies": [
            {"code": cur.get("code"), "name": cur.get("name"), "symbol": cur.get("symbol")}
            for cur in country.get("currencies") or []
            if isinstance(cur, dict)
        ],
        "languages": [
            lang.get("name") for lang in country.get("languages") or [] if isinstance(lang, dict)
        ],
        "borders": country.get("borders") or [],
        "flag_url": (country.get("flag") or {}).get("url_png"),
    }


if __name__ == "__main__":
    mcp.run()
