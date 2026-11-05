from datetime import date, timedelta
from pathlib import Path
import pytest
from pydantic import ValidationError
from engine import Case, value
from research_engine import (
    ReverseDCF,
    reverse_dcf,
    EarningsQuality,
    earnings_quality,
    ScenarioSet,
    WeightedScenario,
    scenario_ensemble,
    specialist_review,
)
from forecasting import MarketBar, ForecastExperiment, evaluate_forecast
from instruments import ingest_rows, search_instruments
from knowledge import save_snapshot, snapshot


@pytest.fixture
def case():
    return Case.model_validate_json(
        (Path(__file__).resolve().parents[1] / "examples/case.json").read_text()
    )


@pytest.mark.parametrize(
    "driver,bounds",
    [
        ("revenue_growth", (-0.1, 0.3)),
        ("ebitda_margin", (0.1, 0.4)),
        ("wacc", (0.08, 0.3)),
    ],
)
def test_reverse_recovers_assumption(case, driver, bounds):
    target = value(case)["base"]["per_share"]
    result = reverse_dcf(
        ReverseDCF(
            case=case,
            market_price=target,
            driver=driver,
            lower=bounds[0],
            upper=bounds[1],
        )
    )
    assert result["status"] == "solved"
    assert result["solutions"][0]["assumption"] == pytest.approx(
        getattr(case.drivers, driver), abs=1e-7
    )


def test_reverse_no_extrapolation(case):
    result = reverse_dcf(
        ReverseDCF(case=case, market_price=10000, lower=-0.01, upper=0.01)
    )
    assert result["status"] == "not_bracketed" and result["solutions"] == []


def test_scenario_probabilities_and_basis(case):
    data = case.model_dump()
    data["drivers"]["revenue_growth"] += 0.02
    other = Case.model_validate(data)
    x = ScenarioSet(
        scenarios=[
            WeightedScenario(name="base", case=case, probability=0.6),
            WeightedScenario(name="bull", case=other, probability=0.4),
        ],
        probability_source="test",
    )
    assert scenario_ensemble(x)["expected_per_share"] == pytest.approx(
        0.6 * value(case)["base"]["per_share"] + 0.4 * value(other)["base"]["per_share"]
    )
    data = x.model_dump()
    data["scenarios"][1]["probability"] = 0.5
    with pytest.raises(ValidationError):
        ScenarioSet.model_validate(data)
    data = x.model_dump()
    data["scenarios"][1]["case"]["currency"] = "USD"
    with pytest.raises(ValidationError):
        ScenarioSet.model_validate(data)


def test_unsupported_scenario_blocks(case):
    data = case.model_dump()
    data["drivers"]["ebitda_margin"] = -0.2
    bad = Case.model_validate(data)
    x = ScenarioSet(
        scenarios=[
            WeightedScenario(name="base", case=case, probability=0.5),
            WeightedScenario(name="bad", case=bad, probability=0.5),
        ],
        probability_source="test",
    )
    assert scenario_ensemble(x)["expected_per_share"] is None


def test_quality_known_values():
    q = earnings_quality(
        EarningsQuality(
            net_income=20,
            operating_cash_flow=10,
            opening_assets=90,
            closing_assets=110,
            revenue=100,
            previous_revenue=100,
            receivables=20,
            previous_receivables=10,
            capex=4,
            stock_compensation=2,
            source="test",
        )
    )
    assert q["accruals_to_average_assets"] == 0.1
    assert q["receivable_days_change"] == 36.5
    assert q["stock_comp_adjusted_fcf"] == 4


def experiment(model="random_walk"):
    bars = [
        MarketBar(
            date=date(2020, 1, 1) + timedelta(days=i),
            open=100 + i,
            high=101 + i,
            low=99 + i,
            close=100 + i,
        )
        for i in range(40)
    ]
    return ForecastExperiment(
        bars=bars,
        minimum_train=20,
        horizon=5,
        model=model,
        source="synthetic",
        adjustment="unadjusted",
    )


def test_walk_forward_no_future_data_and_baseline():
    x = experiment()
    seen = []

    def predictor(history, dates):
        assert max(b.date for b in history) < min(dates)
        seen.append(len(history))
        return [history[-1].close] * len(dates)

    result = evaluate_forecast(x, predictor)
    assert seen == [20, 25, 30, 35]
    assert result["mae_skill"] == 0
    assert result["mae"] == 3
    assert result["observations"] == 20


def test_ar_and_bad_bar():
    assert evaluate_forecast(experiment("ar1"))["mae"] < 3
    with pytest.raises(ValidationError):
        MarketBar(date=date.today(), open=10, close=11, low=12, high=13)


def test_instruments_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("VALUATION_DB", str(tmp_path / "test.sqlite3"))
    ingest_rows(
        [
            dict(
                symbol="ABC.JO",
                name="ABC Ltd",
                country="South Africa",
                exchange="JNB",
                currency="ZAC",
                sector="Industrials",
                industry="Components",
                delisted="False",
            )
        ]
    )
    result = search_instruments("ABC", country="South Africa")
    assert result["total_loaded"] == 1 and result["results"][0]["currency"] == "ZAC"
    assert not search_instruments("' OR 1=1")["results"]
    sid = save_snapshot("test", {"observations": [1, None]})
    assert snapshot(sid)["payload"]["observations"] == [1, None]


def test_plan_does_not_claim_agent_execution(case):
    result = specialist_review(case)
    assert "no LLM" in result["mode"]
    assert len(result["roles"]) == 7
