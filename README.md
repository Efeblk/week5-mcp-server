# Data Explorer MCP Server

Data Explorer is a small STDIO MCP server that gives an MCP client two tools backed
by the [REST Countries](https://restcountries.com) API. It is the Week 4 custom MCP
server assignment.

> **API note:** the course starter used REST Countries v3.1, which needed no key. That
> version was shut down in 2026: every v1–v4 request now returns *"This API version has
> been deprecated"*. This server uses the current **v5** API. v5 needs a free API key
> (1,000 requests/month, no credit card) from https://restcountries.com/sign-up.

## Install

From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`mcp` is pinned below version 2 because this assignment uses the version 1 `FastMCP` API.

## API key

The server reads the key from the `RESTCOUNTRIES_API_KEY` environment variable. It never
hard-codes or logs the key. To save it for your Windows user (open a new terminal afterwards):

```powershell
setx RESTCOUNTRIES_API_KEY "rc_live_..."
```

If the variable is missing, both tools return a clean
`{"error": "RESTCOUNTRIES_API_KEY is not set ..."}` and make no request.

## Run

```powershell
.\.venv\Scripts\python.exe server.py
```

The server uses STDIO, so it will appear to wait for input. An MCP client starts it
and communicates with it; do not type JSON into the terminal by hand.

## Register in an MCP client

### Claude Desktop

Add this entry to Claude Desktop's MCP configuration (`%APPDATA%\Claude\claude_desktop_config.json`).
Replace the paths if this project was cloned somewhere else; Windows paths need doubled
backslashes in JSON.

```json
{
  "mcpServers": {
    "data-explorer": {
      "command": "C:\\Users\\efeba\\.t3\\projects\\dreamlabs-assignments\\week4-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\efeba\\.t3\\projects\\dreamlabs-assignments\\week4-mcp-server\\server.py"
      ],
      "env": { "RESTCOUNTRIES_API_KEY": "rc_live_..." }
    }
  }
}
```

Restart Claude Desktop after saving the configuration.

### Claude Code

```powershell
claude mcp add data-explorer -e RESTCOUNTRIES_API_KEY=$env:RESTCOUNTRIES_API_KEY -- "C:\Users\efeba\.t3\projects\dreamlabs-assignments\week4-mcp-server\.venv\Scripts\python.exe" "C:\Users\efeba\.t3\projects\dreamlabs-assignments\week4-mcp-server\server.py"
```

Then start `claude`, run `/mcp` to check that `data-explorer` is connected, and ask
something like *"Which countries border Germany, and what currency does Japan use?"*

## Tool reference

### `search_countries(query, limit=5)`

Search countries by name (case-insensitive substring match on common, official,
alternate, and native names).

| Parameter | Type | Rules |
| --- | --- | --- |
| `query` | `str` | Required, not empty, at most 100 characters |
| `limit` | `int` | 1–50, default 5 |

Returns `list[dict]` with items `{name, capital, region, population}`. An empty list means
nothing matched.

```text
search_countries(query="germany")
→ [{"name": "Germany", "capital": "Berlin", "region": "Europe", "population": 83491249}]
```

### `get_country_details(name)`

Get one country's details. The name search can match several countries (`"niger"` also
finds Nigeria), so the tool picks the exact common or official name if there is one,
otherwise the first match.

| Parameter | Type | Rules |
| --- | --- | --- |
| `name` | `str` | Required, not empty, at most 100 characters |

Returns `dict` with `name` (`common`, `official`), `capital`, `region`, `subregion`,
`population`, `currencies` (list of `{code, name, symbol}`), `languages` (list of names),
`borders` (list of ISO alpha-3 codes, empty for islands), and `flag_url` (PNG).

```text
get_country_details(name="japan")
→ {"name": {"common": "Japan", "official": "Japan"}, "capital": "Tokyo",
   "region": "Asia", "subregion": "Eastern Asia", "population": 123210000,
   "currencies": [{"code": "JPY", "name": "Japanese yen", "symbol": "¥"}],
   "languages": ["Japanese"], "borders": [],
   "flag_url": "https://flags.restcountries.com/v5/w640/jp.png"}
```

### Errors

Neither tool raises. Errors come back as data the model can read:
`search_countries` returns a one-item list `[{"error": "..."}]` and
`get_country_details` returns `{"error": "..."}`.

| Situation | Message |
| --- | --- |
| Empty / non-string / too long input | `query must not be empty`, `name must be a string`, `name must be 100 characters or fewer` |
| Bad `limit` | `limit must be an integer between 1 and 50` |
| No match | search: `[]`; details: `no country found matching 'atlantis'` |
| Missing key | `RESTCOUNTRIES_API_KEY is not set (...)` |
| Key rejected (401/403) | `API key was rejected (status 401): <API's message>` |
| Rate limited (429) | `API rate limit reached, try again later` |
| Timeout (10 s) | `upstream request timed out` |
| Network failure | `upstream network error: ...` |
| Other HTTP error | `upstream request failed with status 500` |
| Non-JSON / wrong shape | `upstream returned an unexpected response` |

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The tests mock `httpx.get`, so they need no network or key. One live test is skipped by
default; run it with `$env:LIVE = "1"` and a real key set.

## MCP client demo

`client_demo.py` is a real MCP client (`mcp.client.stdio.stdio_client` + `ClientSession`).
It launches `server.py` over STDIO, lists its tools, and calls both tools with good and
bad input.

```powershell
.\.venv\Scripts\python.exe client_demo.py > outputs\client_transcript.txt
```
