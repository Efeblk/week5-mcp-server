"""Run the Data Explorer server through a real MCP STDIO client."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

CALL_TIMEOUT_SECONDS = 15


def show(label: str, value: object) -> None:
    """Print MCP response models as readable JSON for the saved transcript."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    print(f"\n{label}")
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


async def main() -> None:
    server_path = Path(__file__).with_name("server.py")
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    # A fresh STDIO session per call lets the demo continue if an upstream request
    # times out and its server process is still finishing that request.
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            show("Available tools:", tools)


async def call_once(
    parameters: StdioServerParameters, tool_name: str, arguments: dict
) -> object:
    """Call one tool in an independent session so a timeout cannot block later calls."""
    try:
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=CALL_TIMEOUT_SECONDS,
                )
    except TimeoutError:
        return {"error": f"client timed out after {CALL_TIMEOUT_SECONDS} seconds"}
    except Exception as exc:
        return {"error": f"client request failed: {exc}"}


async def run_calls(parameters: StdioServerParameters) -> None:
    calls = [
        ("search_countries(\"germany\")", "search_countries", {"query": "germany"}),
        ("get_country_details(\"japan\")", "get_country_details", {"name": "japan"}),
        (
            "get_country_details(\"united states\")",
            "get_country_details",
            {"name": "united states"},
        ),
        ("get_country_details(\"\")", "get_country_details", {"name": ""}),
        ("get_country_details(\"atlantis\")", "get_country_details", {"name": "atlantis"}),
        (
            "search_countries(\"a\", limit=0)",
            "search_countries",
            {"query": "a", "limit": 0},
        ),
    ]
    for label, tool_name, arguments in calls:
        result = await call_once(parameters, tool_name, arguments)
        show(label + ":", result)


if __name__ == "__main__":
    async def demo() -> None:
        server_path = Path(__file__).with_name("server.py")
        parameters = StdioServerParameters(command=sys.executable, args=[str(server_path)])
        await main()
        await run_calls(parameters)

    asyncio.run(demo())
