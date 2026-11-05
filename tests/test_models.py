from pathlib import Path
import pytest
from pydantic import ValidationError
from engine import Case, value, bridge, dcf
from advanced import (
    CapitalCost,
    capital_cost,
    CashflowMethod,
    cashflow_method,
    Liability,
    liability_value,
    Simulation,
    simulate,
    MacroShock,
    macro_case,
    diagnostics,
)


@pytest.fixture
def case():
    return Case.model_validate_json(
        (Path(__file__).resolve().parents[1] / "examples/case.json").read_text()
    )


def test_statement_identities_and_cashflow(case):
    result = value(case)
    for key in ["statements", "scenario_statements"]:
        cash = case.opening.cash
        for row in result[key]:
            assert row["assets"] == pytest.approx(row["funding"])
            assert row["cash"] == pytest.approx(
                cash + row["cfo"] + row["cfi"] + row["cff"]
            )
            nopat = row["ebit"] - max(row["ebit"], 0) * case.drivers.tax_rate
            assert row["fcff"] == pytest.approx(
                nopat + row["depreciation"] + row["cfi"] - row["change_nwc"]
            )
            cash = row["cash"]


def test_hand_calculated_dcf(case):
    # One annual payment 10, terminal EBIT 20, no growth, tax 25%, WACC 10%.
    data = case.model_dump()
    data["years"] = 1
    data["risks"] = []
    data["drivers"]["tax_rate"] = 0.25
    c = Case.model_validate(data)
    result = dcf(c, [dict(year=1, fcff=10)], 0.1, 0, 20)
    assert result["enterprise_value"] == pytest.approx(
        10 / 1.1 + (20 * 0.75 / 0.1) / 1.1
    )


def test_bridge_other_claims(case):
    before = bridge(case, 100_000_000)
    data = case.model_dump()
    data["opening"]["other_claims"] = 3_000_000
    data["opening"]["non_operating_assets"] = 1_000_000
    after = bridge(Case.model_validate(data), 100_000_000)
    assert after["equity_value"] == before["equity_value"] - 2_000_000


def test_wacc_monotonic_and_sensitivity_center(case):
    result = value(case)
    higher = case.model_dump()
    higher["drivers"]["wacc"] += 0.01
    assert (
        value(Case.model_validate(higher))["base"]["per_share"]
        < result["base"]["per_share"]
    )
    center = next(
        x
        for x in result["sensitivity"]
        if x["wacc"] == case.drivers.wacc
        and x["growth"] == case.drivers.terminal_growth
    )
    assert center["per_share"] == result["base"]["per_share"]


@pytest.mark.parametrize(
    "change",
    [
        {"wacc": 0.04},
        {"terminal_growth": 0.15},
        {"capex_rate": -1},
        {"wacc": float("nan")},
    ],
)
def test_invalid_drivers_rejected(case, change):
    data = case.model_dump()
    data["drivers"].update(change)
    with pytest.raises(ValidationError):
        Case.model_validate(data)


def test_nonpositive_terminal_is_unavailable(case):
    data = case.model_dump()
    data["drivers"]["ebitda_margin"] = -0.1
    assert value(Case.model_validate(data))["base"]["status"] == "unsupported"


def test_capital_cost_known_answer():
    c = CapitalCost(
        risk_free=0.04,
        equity_risk_premium=0.05,
        unlevered_beta=1,
        debt_weight=0.2,
        tax_rate=0.25,
        pretax_cost_debt=0.06,
        source="test",
    )
    r = capital_cost(c)
    assert r["levered_beta"] == pytest.approx(1.1875)
    assert r["wacc"] == pytest.approx(0.0885)


@pytest.mark.parametrize("method", ["fcfe", "dividends", "apv"])
def test_cashflow_methods_closed_form(method):
    m = CashflowMethod(
        method=method,
        cashflows=[10],
        discount_rate=0.1,
        terminal_growth=0,
        terminal_cashflow=10,
        tax_shields=[0] if method == "apv" else [],
        source="test",
    )
    assert cashflow_method(m)["value"] == pytest.approx(100)


def test_residual_income_and_apv_adjustments():
    r = cashflow_method(
        CashflowMethod(
            method="residual_income",
            cashflows=[0, 0],
            discount_rate=0.1,
            opening_book_equity=100,
            source="test",
        )
    )
    assert r["value"] == 100
    a = cashflow_method(
        CashflowMethod(
            method="apv",
            cashflows=[110],
            discount_rate=0.1,
            tax_shields=[11],
            tax_shield_rate=0.1,
            distress_cost_pv=3,
            source="test",
        )
    )
    assert a["value"] == pytest.approx(107)


def test_liability_closed_form_and_duration():
    x = Liability(
        payments=[0, 121], survival=[1, 1], spot_rates=[0.1, 0.1], source="test"
    )
    r = liability_value(x)
    assert r["present_value"] == pytest.approx(100)
    assert r["effective_parallel_duration"] == pytest.approx(2 / 1.1)
    bump = 0.00001
    pvs = []
    for sign in [-1, 1]:
        pvs.append(
            liability_value(
                Liability(
                    payments=x.payments,
                    survival=x.survival,
                    spot_rates=[0.1 + sign * bump] * 2,
                    source="test",
                )
            )["present_value"]
        )
    assert (pvs[0] - pvs[1]) / (2 * bump * 100) == pytest.approx(
        r["effective_parallel_duration"], rel=1e-6
    )


def test_survival_increasing_rejected():
    with pytest.raises(ValidationError):
        Liability(
            payments=[1, 1], survival=[0.9, 0.95], spot_rates=[0.1, 0.1], source="test"
        )


def test_simulation_reproducible_and_zero_variance(case):
    settings = Simulation(draws=100, growth_sd=0, margin_sd=0, wacc_sd=0)
    a = simulate(case, settings)
    assert a == simulate(case, settings)
    assert a["p05"] == a["p95"] == pytest.approx(value(case)["base"]["per_share"])
    assert sum(x["count"] for x in a["histogram"]) == 100


def test_simulation_tails_and_rejections(case):
    s = simulate(case, Simulation(draws=200, wacc_sd=0.15, reference_price=25))
    assert s["rejected"] > 0
    assert s["requested"] == s["accepted"] + s["rejected"]
    assert s["p05"] <= s["p50"] <= s["p95"]
    assert s["loss_expected_shortfall95"] >= s["loss_var95"]
    assert all(x["p05"] <= x["p50"] <= x["p95"] for x in s["fan"])


@pytest.mark.parametrize(
    "matrix",
    [
        [[1, 2, 0], [2, 1, 0], [0, 0, 1]],
        [[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]],
        [[1, 0], [0, 1]],
    ],
)
def test_invalid_correlation(matrix):
    with pytest.raises(ValidationError):
        Simulation(correlation=matrix)


def test_macro_zero_and_adverse_transmission(case):
    assert (
        macro_case(case, MacroShock(source="test"))["result"]["base"]
        == value(case)["base"]
    )
    r = macro_case(
        case, MacroShock(real_growth_delta_pp=-2, fx_depreciation_pct=10, source="test")
    )
    assert r["result"]["base"]["per_share"] < value(case)["base"]["per_share"]


def test_diagnostics_and_peer_exclusion(case):
    data = case.model_dump()
    data["peers"].append(
        dict(name="loss", enterprise_value=100, forward_ebitda=-10, source="test")
    )
    a = diagnostics(Case.model_validate(data))
    assert not a["peers"][-1]["eligible"]
    assert a["peer_quartiles"] == [6.5, 7, 7.5]
    for r in a["ratios"]:
        assert r["economic_profit"] == pytest.approx(
            (r["roic"] - case.drivers.wacc) * r["invested_capital_open"]
        )
