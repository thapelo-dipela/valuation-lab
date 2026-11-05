"""MCP must register and invoke the same engine rather than merely import."""

import asyncio
import json
from pathlib import Path


def test_mcp_registration_and_valuation():
    from mcp_server import server

    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert {
        "run_valuation",
        "analyze_case",
        "search_knowledge",
        "solve_reverse_dcf",
        "plan_research",
        "discover_instruments",
    } <= names
    case = json.loads(
        (Path(__file__).resolve().parents[1] / "examples/case.json").read_text()
    )
    output = asyncio.run(server.call_tool("run_valuation", {"case": case}))
    # FastMCP returns both content and structured output for this typed tool.
    assert output[1]["base"]["status"] == "ok"
