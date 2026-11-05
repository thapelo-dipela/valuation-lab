from datetime import date
from pathlib import Path
import pytest
from pydantic import ValidationError
from accounting import Accounts, analyze, fx_quote
from engine import Case, value
from advanced import MacroShock, macro_case, diagnostics

ROOT = Path(__file__).resolve().parents[1]


def period(year=2024, **changes):
    p = dict(
        year=year,
        revenue=1000,
        cost_of_sales=500,
        operating_expenses=200,
        depreciation=50,
        interest=20,
        tax=46,
        cash=100,
        receivables=100,
        inventory=100,
        ppe=500,
        payables=100,
        debt=300,
        equity=400,
        cfo=200,
        capex=70,
        diluted_shares=100,
    )
    return p | changes


def test_accounts_known_values_and_average_balances():
    r = analyze(
        Accounts(
            currency="USD", source="Test statements", periods=[period(2023), period()]
        )
    )["rows"]
    assert r[0]["roe"] is None
    assert r[1]["net_income"] == 184
    assert r[1]["eps"] == 1.84
    assert r[1]["roe"] == pytest.approx(0.46)
    assert r[1]["dso"] == 36.5
    assert r[1]["fcf"] == 130
    assert r[1]["cash_cycle"] == 36.5


def test_accounts_reject_unbalanced_duplicates_and_nonfinite():
    for periods in [
        [period(equity=1)],
        [period(), period()],
        [period(revenue=float("nan"))],
    ]:
        with pytest.raises(ValidationError):
            Accounts(currency="USD", source="Test", periods=periods)


def test_annual_schedule_and_macro_reconcile():
    case = Case.model_validate_json((ROOT / "examples/case.json").read_text())
    payload = case.model_dump()
    payload["annual_drivers"] = [case.drivers.model_dump() for _ in range(case.years)]
    payload["annual_drivers"][0]["revenue_growth"] = 0.2
    scheduled = Case.model_validate(payload)
    result = value(scheduled)
    assert result["statements"][0]["revenue"] == pytest.approx(
        case.opening.revenue * 1.2
    )
    assert all(r["assets"] == pytest.approx(r["funding"]) for r in result["statements"])
    changed = macro_case(scheduled, MacroShock(real_growth_delta_pp=-2, source="Test"))
    assert changed["result"]["inputs"]["annual_drivers"][0]["revenue_growth"] < 0.2
    tornado = diagnostics(scheduled)["tornado"]
    assert tornado[0]["low_input_value"] != tornado[0]["high_input_value"]


def test_fx_pair_date_and_rate_validation(monkeypatch):
    import accounting

    def quote(data):
        return dict(data=data, url="test", sha256="hash", retrieved_at="test")

    monkeypatch.setattr(
        accounting,
        "fetch_json",
        lambda url: quote(dict(base="USD", quote="EUR", date="2025-01-02", rate=0.9)),
    )
    assert fx_quote("USD", "EUR", date(2025, 1, 3))["rate"] == 0.9
    monkeypatch.setattr(
        accounting,
        "fetch_json",
        lambda url: quote(dict(base="USD", quote="EUR", date="2025-01-04", rate=0.9)),
    )
    with pytest.raises(ValueError):
        fx_quote("USD", "EUR", date(2025, 1, 3))
    assert fx_quote("USD", "USD", date(2025, 1, 3))["rate"] == 1
