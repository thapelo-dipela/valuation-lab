from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
import httpx
from fastapi.responses import FileResponse, JSONResponse, Response

from engine import Case, value
from exports import render
from advanced import (
    CapitalCost,
    CashflowMethod,
    Liability,
    MacroShock,
    Simulation,
    capital_cost,
    cashflow_method,
    liability_value,
    macro_case,
    simulate,
    diagnostics,
)
from engine import Input
import knowledge
from workflow import EvidenceRecord, review_workflow
from providers import world_bank
from research_engine import (
    ReverseDCF,
    reverse_dcf,
    EarningsQuality,
    earnings_quality,
    ScenarioSet,
    scenario_ensemble,
    specialist_review,
)
from forecasting import ForecastExperiment, evaluate_forecast
from instruments import search_instruments, repository_catalog

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Valuation Lab", version="0.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


class AnalysisRequest(Input):
    case: Case
    simulation: Simulation | None = None
    save: bool = False


class MacroRequest(Input):
    case: Case
    shock: MacroShock


@app.post("/api/v1/analysis")
def analysis(request: AnalysisRequest):
    result = value(request.case)
    details = diagnostics(request.case)
    risk = simulate(request.case, request.simulation) if request.simulation else None
    run_id = knowledge.save_run(result, details, risk) if request.save else None
    return dict(
        result=result,
        analysis=details,
        simulation=risk,
        run_id=run_id,
        workflow=review_workflow(request.case, result),
        research_plan=specialist_review(request.case),
    )


@app.post("/api/v1/research/reverse-dcf")
def reverse_calculator(request: ReverseDCF):
    return reverse_dcf(request)


@app.post("/api/v1/research/earnings-quality")
def quality_calculator(request: EarningsQuality):
    return earnings_quality(request)


@app.post("/api/v1/research/scenarios")
def weighted_cases(request: ScenarioSet):
    return scenario_ensemble(request)


@app.post("/api/v1/research/plan")
def research_plan(case: Case):
    return specialist_review(case)


@app.post("/api/v1/research/forecast-evaluation")
def forecast_experiment(request: ForecastExperiment):
    try:
        return evaluate_forecast(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/v1/instruments")
def instruments(
    q: str = Query("", max_length=100),
    country: str = "",
    sector: str = "",
    exchange: str = "",
    limit: int = Query(50, ge=1, le=100),
):
    return search_instruments(q, country, sector, exchange, limit=limit)


@app.get("/api/v1/repositories")
def repositories():
    return repository_catalog()


@app.post("/api/v1/methods/capital-cost")
def cost_method(inputs: CapitalCost):
    return capital_cost(inputs)


@app.post("/api/v1/methods/cashflows")
def cashflow_calculator(inputs: CashflowMethod):
    return cashflow_method(inputs)


@app.post("/api/v1/methods/liability")
def liability_calculator(inputs: Liability):
    return liability_value(inputs)


@app.post("/api/v1/macro")
def macro(request: MacroRequest):
    try:
        return macro_case(request.case, request.shock)
    except ValidationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get("/api/v1/knowledge")
def knowledge_search(
    q: str = Query("", max_length=200), domain: str = Query("", max_length=100)
):
    return knowledge.search(q, domain)


@app.get("/api/v1/knowledge/{skill_id}")
def skill(skill_id: str):
    text = knowledge.skill_text(skill_id)
    if text is None:
        raise HTTPException(404, "Skill not found")
    return dict(markdown=text)


@app.get("/api/v1/runs")
def history():
    return knowledge.runs()


@app.get("/api/v1/runs/{run_id}")
def run_detail(run_id: str):
    record = knowledge.runs(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    evidence = knowledge.evidence_for(run_id)
    result = record["payload"]["result"]
    return dict(
        **record,
        evidence=evidence,
        workflow=review_workflow(
            Case.model_validate(result["inputs"]), result, evidence
        ),
    )


@app.post("/api/v1/runs/{run_id}/evidence", status_code=201)
def add_evidence(run_id: str, record: EvidenceRecord):
    saved = knowledge.record_evidence(run_id, record)
    if saved is None:
        raise HTTPException(404, "Run not found")
    return saved


@app.get("/api/v1/data/world-bank")
def macro_data(
    country: str = "ZAF",
    indicator: str = "gdp_growth",
    start: int = 2015,
    end: int = 2025,
):
    try:
        packet = world_bank(country, indicator, start, end)
        packet["snapshot_id"] = knowledge.save_snapshot("World Bank", packet)
        return packet
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            502, "Official data provider unavailable; retry later"
        ) from exc


@app.get("/api/v1/data/snapshots/{snapshot_id}")
def data_snapshot(snapshot_id: str):
    record = knowledge.snapshot(snapshot_id)
    if not record:
        raise HTTPException(404, "Data snapshot not found")
    return record


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/v1/example")
def example():
    return JSONResponse(
        Case.model_validate_json(
            (ROOT / "examples" / "case.json").read_text()
        ).model_dump(mode="json")
    )


@app.post("/api/v1/valuation")
def valuation(case: Case):
    return value(case)


@app.post("/api/v1/export/{kind}")
def export(kind: Literal["docx", "xlsx", "pptx"], case: Case):
    return Response(
        render(kind, value(case)),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="valuation.{kind}"'},
    )
