from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response

from engine import Case, value
from exports import render

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Valuation Lab", version="0.1.0")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/v1/example")
def example():
    return JSONResponse(Case.model_validate_json((ROOT / "examples" / "case.json").read_text()).model_dump(mode="json"))


@app.post("/api/v1/valuation")
def valuation(case: Case):
    return value(case)


@app.post("/api/v1/export/{kind}")
def export(kind: Literal["docx", "xlsx", "pptx"], case: Case):
    return Response(render(kind, value(case)), media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="valuation.{kind}"'})
