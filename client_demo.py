"""Drive the Data Explorer server through a real MCP STDIO client.

Starts server.py as a subprocess, lists its tools, and calls each one with good and
bad input. Needs RESTCOUNTRIES_API_KEY set (the server inherits this environment).
Run:  python client_demo.py > outputs/client_transcript.txt
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

CALLS = [
    ("search_countries", {"query": "germany"}),
    ("search_countries", {"query": "guinea", "limit": 3}),
    ("get_country_details", {"name": "japan"}),
    ("get_country_details", {"name": "united states"}),
    ("get_country_details", {"name": ""}),
    ("get_country_details", {"name": "atlantis"}),
    ("search_countries", {"query": "a", "limit": 0}),
]


async def main() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("server.py"))],
        env=dict(os.environ),
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                params = ", ".join(tool.inputSchema.get("properties", {}))
                print(f"  - {tool.name}({params})")

            for tool_name, arguments in CALLS:
                result = await session.call_tool(tool_name, arguments)
                args = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
                print(f"\n>>> {tool_name}({args})")
                for block in result.content:
                    print(getattr(block, "text", block))


if __name__ == "__main__":
    asyncio.run(main())
