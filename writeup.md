# Data Explorer write-up

## Transcript

This is the real stdout captured from `client_demo.py` in
`outputs/client_transcript.txt`. The MCP connection and tool discovery succeeded, but
the live REST Countries v3.1 service was deprecated during this run. It returned a
non-list deprecation payload instead of country data, so the server returned its clean
`upstream returned an unexpected response` error. The Japan request also recorded the
client SDK TaskGroup error shown below. This output has not been replaced with made-up
country data.

```text

Available tools:
{
  "meta": null,
  "nextCursor": null,
  "tools": [
    {
      "name": "search_countries",
      "title": null,
      "description": "Search country names and return name, capital, region, and population.",
      "inputSchema": {
        "properties": {
          "query": {
            "title": "Query",
            "type": "string"
          },
          "limit": {
            "default": 5,
            "title": "Limit",
            "type": "integer"
          }
        },
        "required": [
          "query"
        ],
        "title": "search_countriesArguments",
        "type": "object"
      },
      "outputSchema": {
        "properties": {
          "result": {
            "items": {
              "additionalProperties": true,
              "type": "object"
            },
            "title": "Result",
            "type": "array"
          }
        },
        "required": [
          "result"
        ],
        "title": "search_countriesOutput",
        "type": "object"
      },
      "icons": null,
      "annotations": null,
      "meta": null,
      "execution": null
    },
    {
      "name": "get_country_details",
      "title": null,
      "description": "Return detailed country information for an exact name when possible.",
      "inputSchema": {
        "properties": {
          "name": {
            "title": "Name",
            "type": "string"
          }
        },
        "required": [
          "name"
        ],
        "title": "get_country_detailsArguments",
        "type": "object"
      },
      "outputSchema": null,
      "icons": null,
      "annotations": null,
      "meta": null,
      "execution": null
    }
  ]
}

search_countries("germany"):
{
  "meta": null,
  "content": [
    {
      "type": "text",
      "text": "{\n  \"error\": \"upstream returned an unexpected response\"\n}",
      "annotations": null,
      "meta": null
    }
  ],
  "structuredContent": {
    "result": [
      {
        "error": "upstream returned an unexpected response"
      }
    ]
  },
  "isError": false
}

get_country_details("japan"):
{
  "error": "client request failed: unhandled errors in a TaskGroup (1 sub-exception)"
}

get_country_details("united states"):
{
  "meta": null,
  "content": [
    {
      "type": "text",
      "text": "{\n  \"error\": \"upstream returned an unexpected response\"\n}",
      "annotations": null,
      "meta": null
    }
  ],
  "structuredContent": null,
  "isError": false
}

get_country_details(""):
{
  "meta": null,
  "content": [
    {
      "type": "text",
      "text": "{\n  \"error\": \"name must not be empty\"\n}",
      "annotations": null,
      "meta": null
    }
  ],
  "structuredContent": null,
  "isError": false
}

get_country_details("atlantis"):
{
  "meta": null,
  "content": [
    {
      "type": "text",
      "text": "{\n  \"error\": \"upstream returned an unexpected response\"\n}",
      "annotations": null,
      "meta": null
    }
  ],
  "structuredContent": null,
  "isError": false
}

search_countries("a", limit=0):
{
  "meta": null,
  "content": [
    {
      "type": "text",
      "text": "{\n  \"error\": \"limit must be an integer between 1 and 50\"\n}",
      "annotations": null,
      "meta": null
    }
  ],
  "structuredContent": {
    "result": [
      {
        "error": "limit must be an integer between 1 and 50"
      }
    ]
  },
  "isError": false
}
```

## How I handled errors

Both tools first validate that the country name is a string, is not empty after
trimming whitespace, and is no longer than 100 characters. The search tool also
validates that `limit` is an integer from 1 through 50 before making a request.

`_get_json` is the shared HTTP helper. It URL-encodes country names before the caller
builds the path, sends a small `fields` query parameter, follows the service's
redirect, and applies a ten-second timeout. It converts timeout, network, other HTTP,
HTTP-status, and invalid-JSON failures into short messages instead of letting an
exception leave a tool. A search 404 returns `[]`; the detail tool tries its fallback
search after a full-text 404 and otherwise returns a no-country-found error.

The detail tool only reads optional API fields with defaults. It turns currencies into
a list of code/name/symbol objects, languages into a list of names, and missing borders
into an empty list.

## Driving from an MCP client (Claude Desktop / IDE)

<!-- TODO (you): paste a screenshot or transcript from Claude Desktop / Claude Code calling both tools -->

## What I learned

<!-- TODO (you): write this yourself, 3–5 sentences on controlling what context an agent can reach. Course policy (Week 1 slides, p.16): no AI for reflections. -->
