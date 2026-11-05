"""Local MCP transport. Launch with python mcp_server.py."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from engine import Case, value
from advanced import (
    Simulation,
    diagnostics,
    simulate,
    CapitalCost,
    capital_cost,
    CashflowMethod,
    cashflow_method,
    Liability,
    liability_value,
    MacroShock,
    macro_case,
)
import knowledge
from workflow import review_workflow
from research_engine import (
    ReverseDCF,
    reverse_dcf,
    EarningsQuality,
    earnings_quality,
    specialist_review,
    ScenarioSet,
    scenario_ensemble,
)
from forecasting import ForecastExperiment, evaluate_forecast
from instruments import search_instruments

server = FastMCP("Valuation Lab")


@server.tool()
def solve_reverse_dcf(inputs: ReverseDCF) -> dict[str, object]:
    """Solve market-implied growth, margin or WACC with explicit search bounds."""
    return reverse_dcf(inputs)


@server.tool()
def screen_earnings_quality(inputs: EarningsQuality) -> dict[str, object]:
    return earnings_quality(inputs)


@server.tool()
def plan_research(case: Case) -> dict[str, object]:
    """Prepare specialist, bull/bear and chair tasks; no model calls or invented consensus."""
    return specialist_review(case)


@server.tool()
def evaluate_scenarios(inputs: ScenarioSet) -> dict[str, object]:
    return scenario_ensemble(inputs)


@server.tool()
def evaluate_market_forecast(inputs: ForecastExperiment) -> dict[str, object]:
    return evaluate_forecast(inputs)


@server.tool()
def discover_instruments(
    query: str = "", country: str = "", sector: str = "", exchange: str = ""
) -> dict[str, object]:
    return search_instruments(query, country, sector, exchange)


@server.tool(structured_output=True)
def analyze_case(case: Case, simulation: Simulation | None = None) -> dict[str, object]:
    """Return valuation, diagnostics, workflow gates and optional reproducible risk distribution."""
    result = value(case)
    return dict(
        result=result,
        analysis=diagnostics(case),
        workflow=review_workflow(case, result),
        simulation=simulate(case, simulation) if simulation else None,
    )


@server.tool()
def search_knowledge(query: str = "", domain: str = "") -> dict[str, object]:
    """Retrieve original CFA-oriented method cards with primary source links and limitations."""
    return knowledge.search(query, domain)


@server.tool()
def read_skill(skill_id: str) -> dict[str, object]:
    """Read the full discipline workflow for a retrieved method card."""
    return dict(markdown=knowledge.skill_text(skill_id))


@server.tool()
def calculate_capital_cost(inputs: CapitalCost) -> dict[str, object]:
    return capital_cost(inputs)


@server.tool()
def calculate_cashflow_method(inputs: CashflowMethod) -> dict[str, object]:
    return cashflow_method(inputs)


@server.tool()
def calculate_liability(inputs: Liability) -> dict[str, object]:
    return liability_value(inputs)


@server.tool()
def evaluate_macro(case: Case, shock: MacroShock) -> dict[str, object]:
    return macro_case(case, shock)


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
