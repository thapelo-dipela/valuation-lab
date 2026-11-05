"""Evidence review gates; checks never imply professional sign-off."""

from datetime import date
from typing import Annotated, Literal
from pydantic import Field, HttpUrl, model_validator
from engine import Input, Evidence, Case


class EvidenceRecord(Input):
    claim: Evidence
    input_path: Evidence
    source_url: HttpUrl
    publisher: Evidence
    published_date: date
    retrieved_date: date
    period: Evidence
    units: Evidence
    kind: Literal["reported", "guidance", "analyst_assumption", "synthetic"]
    locator: Evidence
    review: Literal["unreviewed", "corroborated", "conflicted"] = "unreviewed"
    notes: Annotated[str, Field(max_length=4000)] = ""

    @model_validator(mode="after")
    def chronology(self):
        if self.published_date > self.retrieved_date:
            raise ValueError("Publication must not follow retrieval")
        return self


def review_workflow(case: Case, result, evidence=None):
    evidence = evidence or []
    synthetic = any(
        "fictional" in s.lower() or "synthetic" in s.lower()
        for s in [case.opening.source, case.drivers.source]
    )
    conflicts = [e for e in evidence if e["review"] == "conflicted"]
    future = [
        e for e in evidence if e["published_date"] > case.valuation_date.isoformat()
    ]
    required = {
        "opening",
        "drivers.wacc",
        "drivers.terminal_growth",
        "drivers.terminal_roic",
        "drivers.revenue_growth",
        "drivers.ebitda_margin",
    }
    covered = {
        e["input_path"]
        for e in evidence
        if e["review"] == "corroborated"
        and e["kind"] != "synthetic"
        and e["published_date"] <= case.valuation_date.isoformat()
    }
    missing = sorted(required - covered)
    return dict(
        status="research_required"
        if synthetic or conflicts or future or missing
        else "ready_for_independent_review",
        gates=[
            dict(
                stage="01 / Mandate",
                status="review",
                detail="Confirm purpose, basis, perimeter and currency with the analyst.",
            ),
            dict(
                stage="Sources",
                status="blocked"
                if missing or conflicts or future or synthetic
                else "pass",
                detail=(
                    "You are exploring fictional data. Calculations work; add real financial statements and support your assumptions before using the results for research. "
                    if synthetic
                    else ""
                )
                + (
                    "Still needed: "
                    + ", ".join(
                        path.replace("drivers.", "").replace("_", " ")
                        for path in missing
                    )
                    + ". "
                    if missing
                    else "Required assumptions have source records. "
                )
                + f"{len(conflicts)} conflicting sources; {len(future)} sources published after the valuation date.",
            ),
            dict(
                stage="03 / Reconcile",
                status="warning" if result["checks"] else "pass",
                detail="; ".join(result["checks"])
                or "Opening and projected statements reconcile.",
            ),
            dict(
                stage="04 / Challenge",
                status="review",
                detail="Test terminal economics, peer normalization, macro transmission and distribution calibration.",
            ),
            dict(
                stage="05 / Communicate",
                status="review",
                detail="Publish methods, exclusions, sensitivities, source dates and limitations; obtain independent review.",
            ),
        ],
        missing_evidence=missing,
        synthetic=synthetic,
        not_a_signoff=True,
    )
