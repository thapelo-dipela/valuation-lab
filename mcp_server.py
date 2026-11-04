"""Local MCP transport. Launch with python mcp_server.py."""
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from engine import Case, value

server = FastMCP("Valuation Lab")


@server.tool(structured_output=True)
def run_valuation(case: Case) -> dict[str, object]:
    """Calculate a deterministic operating-company valuation and reconciled forecasts."""
    return value(case)


@server.tool()
def valuation_input_schema() -> dict[str, object]:
    """Return the JSON Schema for a valuation case, including ESG scenario inputs."""
    return Case.model_json_schema()


@server.resource("valuation://skills/reasoning")
def reasoning_skill() -> str:
    """Read the analyst workflow for evidence-backed valuation scenarios."""
    return (Path(__file__).parent / "skills/valuation-reasoning/SKILL.md").read_text()


if __name__ == "__main__":
    server.run(transport="stdio")
