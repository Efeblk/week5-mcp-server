# Data Explorer MCP Server

Data Explorer is a small STDIO MCP server that gives an MCP client two tools backed
by the REST Countries API. It is the Week 4 custom MCP server assignment.

## Install

From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The project pins `mcp` below version 2 because this assignment uses the version 1
`FastMCP` API.

## Run

```powershell
.\.venv\Scripts\python.exe server.py
```

The server uses STDIO, so it will appear to wait for input. An MCP client starts it
and communicates with it; do not type JSON into the terminal by hand.

## Register an MCP client

### Claude Desktop

Add this entry to Claude Desktop's MCP configuration. Replace the paths if this
project was cloned somewhere else. Windows paths need doubled backslashes in JSON.

```json
{
  "mcpServers": {
    "data-explorer": {
      "command": "C:\\Users\\efeba\\.t3\\projects\\dreamlabs-assignments\\week4-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\efeba\\.t3\\projects\\dreamlabs-assignments\\week4-mcp-server\\server.py"
      ]
    }
  }
}
```

Restart Claude Desktop after saving the configuration.

### Claude Code

In PowerShell, register the same executable and server file with:

```powershell
claude mcp add data-explorer -- "C:\Users\efeba\.t3\projects\dreamlabs-assignments\week4-mcp-server\.venv\Scripts\python.exe" "C:\Users\efeba\.t3\projects\dreamlabs-assignments\week4-mcp-server\server.py"
```

## Tool reference

| Tool | Parameters | Return shape | Example input | Example output |
| --- | --- | --- | --- | --- |
| `search_countries` | `query: str`, `limit: int = 5` (1–50) | `list[dict]`, where each item has `name`, `capital`, `region`, and `population` | `{"query": "germany"}` | `[{"name": "Germany", "capital": "Berlin", "region": "Europe", "population": 83240525}]` |
| `get_country_details` | `name: str` | `dict` with `name` (`common`, `official`), `capital`, `region`, `subregion`, `population`, `currencies`, `languages`, `borders`, and `flag_url` | `{"name": "japan"}` | `{"name": {"common": "Japan", "official": "Japan"}, "capital": "Tokyo", "currencies": [{"code": "JPY", "name": "Japanese yen", "symbol": "¥"}], "languages": ["Japanese"], "borders": [], "flag_url": "https://..."}` |

`get_country_details` first asks REST Countries for an exact `fullText=true` name
match. If that returns 404, it tries a broader name search and chooses an exact common
or official name when one is available.

Both tools return clean data rather than raising exceptions. `search_countries` uses
an error item such as `[{"error": "query must not be empty"}]`; a no-result search is
`[]`. `get_country_details` uses an error object such as
`{"error": "no country found matching 'atlantis'"}`. Upstream timeouts, network
failures, invalid JSON, and HTTP failures also return an `error` message; HTTP failure
messages include the status code (for example, `status 500`).

## Tests

Install the development requirements, then run the mocked unit tests:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

One test is intentionally skipped by default because it calls the public service. Run
it only when you want a live check:

```powershell
$env:LIVE = "1"
.\.venv\Scripts\python.exe -m pytest -q
```

## MCP client demo

`client_demo.py` is a real client made with `mcp.client.stdio.stdio_client` and
`ClientSession`. It launches `server.py`, lists its tools, and calls each required
success and error example.

```powershell
.\.venv\Scripts\python.exe client_demo.py
```

The captured run is saved in `outputs/client_transcript.txt`. See `writeup.md` for the
embedded transcript and the current live-API result.
