# Data Explorer write-up

## Transcript

Real output of `client_demo.py` (saved in `outputs/client_transcript.txt`). The script is
an MCP client: it starts `server.py` over STDIO, lists the tools, and calls both of them
with good and bad input.

```text
Available tools:
  - search_countries(query, limit)
  - get_country_details(name)

>>> search_countries(query='germany')
{
  "name": "Germany",
  "capital": "Berlin",
  "region": "Europe",
  "population": 83298787
}

>>> search_countries(query='guinea', limit=3)
{
  "name": "Equatorial Guinea",
  "capital": "Malabo",
  "region": "Africa",
  "population": 1795834
}
{
  "name": "Guinea",
  "capital": "Conakry",
  "region": "Africa",
  "population": 17521167
}
{
  "name": "Guinea-Bissau",
  "capital": "Bissau",
  "region": "Africa",
  "population": 1890252
}

>>> get_country_details(name='japan')
{
  "name": {
    "common": "Japan",
    "official": "Japan"
  },
  "capital": "Tokyo",
  "region": "Asia",
  "subregion": "Eastern Asia",
  "population": 122650000,
  "currencies": [
    {
      "code": "JPY",
      "name": "Japanese yen",
      "symbol": "¥"
    }
  ],
  "languages": [
    "Japanese"
  ],
  "borders": [],
  "flag_url": "https://flags.restcountries.com/v5/w640/jp.png"
}

>>> get_country_details(name='united states')
{
  "name": {
    "common": "United States",
    "official": "United States of America"
  },
  "capital": "Washington, D.C.",
  "region": "Americas",
  "subregion": "North America",
  "population": 341784857,
  "currencies": [
    {
      "code": "USD",
      "name": "United States dollar",
      "symbol": "$"
    }
  ],
  "languages": [
    "English"
  ],
  "borders": [
    "CAN",
    "MEX"
  ],
  "flag_url": "https://flags.restcountries.com/v5/w640/us.png"
}

>>> get_country_details(name='')
{
  "error": "name must not be empty"
}

>>> get_country_details(name='atlantis')
{
  "error": "no country found matching 'atlantis'"
}

>>> search_countries(query='a', limit=0)
{
  "error": "limit must be an integer between 1 and 50"
}
```

## How I handled errors

The REST Countries v3.1 API from the starter was shut down while I was doing this
assignment: every request redirected to a JSON body saying *"This API version has been
deprecated"*. The first version of my server caught this, because the body was not the
list it expected, and returned `upstream returned an unexpected response` instead of
crashing. I then moved the server to the v5 API, which needs a free API key.

- **Input validation first.** Both tools check that the name is a string, not empty
  after trimming, and at most 100 characters. `search_countries` also checks that
  `limit` is an int from 1 to 50 (and not a bool, because `True` is an int in Python).
  Bad input returns an error before any request is made.
- **One HTTP helper.** `_search_by_name` makes the request for both tools. It returns
  `(countries, None)` on success or `(None, message)` on failure, so each tool only
  checks for an error and formats the result. It handles a missing API key, timeouts
  (10 s), network errors, a rejected key (401/403, including the API's own message),
  rate limiting (429), other HTTP errors (with the status code), and a body that is not
  JSON or not the expected `{"data": {"objects": [...]}}` shape.
- **No match is not an error for search.** `search_countries` returns `[]`, but
  `get_country_details` returns `{"error": "no country found matching ..."}`, because
  it promises one country.
- **Missing fields.** The tools read every API field with a default (`or []`, `or {}`),
  so a country without a capital or borders gives `None` / `[]` rather than a
  `KeyError`.
- **Errors are data.** The tools never raise. The error messages are short and say what
  went wrong, so the agent can tell the user or retry with different input.

The mocked tests in `tests/test_server.py` cover each of these cases (18 pass).

## Driving from an MCP client (Claude Desktop / IDE)

<!-- TODO (you): register the server (README → "Register in an MCP client"), ask a question that uses both tools, and paste a screenshot or the chat here. -->

## What I learned

<!-- TODO (you): write this yourself, 3–5 sentences on controlling what context an agent can reach. Course policy (Week 1 slides, p.16): no AI for reflections. -->
