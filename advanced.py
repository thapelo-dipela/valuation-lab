"""Auditable analytical methods. Annual end-of-period convention throughout."""

from math import ceil
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator, ValidationError

from engine import Input, Case, Fraction, Amount, Signed, Evidence, project, dcf, value


class CapitalCost(Input):
    risk_free: Annotated[float, Field(ge=0, le=0.5)]
    equity_risk_premium: Fraction
    unlevered_beta: Annotated[float, Field(ge=0, le=5)]
    debt_weight: Annotated[float, Field(ge=0, lt=1)]
    tax_rate: Fraction
    pretax_cost_debt: Fraction
    country_premium: Fraction = 0
    country_exposure: Annotated[float, Field(ge=0, le=3)] = 1
    source: Evidence


def capital_cost(x: CapitalCost):
    beta = x.unlevered_beta * (
        1 + (1 - x.tax_rate) * x.debt_weight / (1 - x.debt_weight)
    )
    equity = (
        x.risk_free
        + beta * x.equity_risk_premium
        + x.country_exposure * x.country_premium
    )
    debt = x.pretax_cost_debt * (1 - x.tax_rate)
    return dict(
        levered_beta=beta,
        cost_equity=equity,
        after_tax_cost_debt=debt,
        wacc=equity * (1 - x.debt_weight) + debt * x.debt_weight,
        assumptions=[
            "Market-value capital weights; zero debt beta in relevering.",
            "Tax shield assumed usable; avoid double-counting country risk.",
        ],
        source=x.source,
    )


class CashflowMethod(Input):
    method: Literal["fcfe", "dividends", "apv", "residual_income"]
    cashflows: Annotated[list[Signed], Field(min_length=1, max_length=100)]
    discount_rate: Annotated[float, Field(gt=0, le=2)]
    terminal_growth: Annotated[float, Field(ge=-0.5, le=0.3)] = 0
    terminal_cashflow: Signed = 0
    opening_book_equity: Amount = 0
    # APV tax shields must be explicit, with their own discount rate. No hidden perpetuity.
    tax_shields: Annotated[list[Amount], Field(max_length=100)] = Field(
        default_factory=list
    )
    tax_shield_rate: Annotated[float, Field(gt=0, le=2)] = 0.1
    distress_cost_pv: Amount = 0
    source: Evidence

    @model_validator(mode="after")
    def constraints(self):
        if self.discount_rate - self.terminal_growth < 0.001:
            raise ValueError(
                "Discount rate must exceed growth by at least 10 basis points"
            )
        if self.method != "apv" and (self.tax_shields or self.distress_cost_pv):
            raise ValueError("Tax shields and distress adjustments belong only to APV")
        if self.method == "apv" and len(self.tax_shields) != len(self.cashflows):
            raise ValueError("APV requires one tax shield per forecast period")
        if self.method != "residual_income" and self.opening_book_equity:
            raise ValueError("Opening book equity belongs only to residual income")
        return self


def cashflow_method(x: CashflowMethod):
    factors = [(1 + x.discount_rate) ** (i + 1) for i in range(len(x.cashflows))]
    explicit = sum(c / f for c, f in zip(x.cashflows, factors))
    terminal = x.terminal_cashflow / (x.discount_rate - x.terminal_growth) / factors[-1]
    shields = sum(
        c / (1 + x.tax_shield_rate) ** (i + 1) for i, c in enumerate(x.tax_shields)
    )
    total = explicit + terminal + shields - x.distress_cost_pv + x.opening_book_equity
    return dict(
        method=x.method,
        value=total,
        value_basis="enterprise" if x.method == "apv" else "equity",
        explicit_pv=explicit,
        terminal_pv=terminal,
        tax_shields_pv=shields,
        opening_book_equity=x.opening_book_equity,
        distress_cost_pv=x.distress_cost_pv,
        convention="terminal_cashflow is the first cash flow AFTER the explicit horizon",
        limitations="Residual income inputs must be NI minus cost of equity times opening book equity; clean-surplus accounting required. APV excludes terminal tax shields unless separately modeled.",
        source=x.source,
    )


class Liability(Input):
    payments: Annotated[list[Amount], Field(min_length=1, max_length=100)]
    survival: Annotated[list[Fraction], Field(min_length=1, max_length=100)]
    spot_rates: Annotated[list[float], Field(min_length=1, max_length=100)]
    source: Evidence

    @model_validator(mode="after")
    def constraints(self):
        if not len(self.payments) == len(self.survival) == len(self.spot_rates):
            raise ValueError("Payment, survival and spot-rate lengths must match")
        if any(not -0.5 <= x <= 2 for x in self.spot_rates):
            raise ValueError("Spot rates must be between -50% and 200%")
        if any(b > a for a, b in zip([1] + self.survival, self.survival)):
            raise ValueError(
                "Unconditional survival probabilities must be non-increasing"
            )
        return self


def liability_value(x: Liability):
    expected = [c * s for c, s in zip(x.payments, x.survival)]
    pv = [
        c / (1 + r) ** (i + 1) for i, (c, r) in enumerate(zip(expected, x.spot_rates))
    ]
    total = sum(pv)
    duration = (
        sum((i + 1) * p / (1 + r) for i, (p, r) in enumerate(zip(pv, x.spot_rates)))
        / total
        if total
        else None
    )
    convexity = (
        sum(
            (i + 1) * (i + 2) * p / (1 + r) ** 2
            for i, (p, r) in enumerate(zip(pv, x.spot_rates))
        )
        / total
        if total
        else None
    )
    return dict(
        present_value=total,
        expected_payments=expected,
        period_pv=pv,
        effective_parallel_duration=duration,
        parallel_convexity=convexity,
        scope="Survival-contingent end-year payments only; no death benefit, expenses, lapse, risk margin or regulatory capital.",
        source=x.source,
    )


class MacroShock(Input):
    real_growth_delta_pp: Annotated[float, Field(ge=-30, le=30)] = 0
    inflation_delta_pp: Annotated[float, Field(ge=-30, le=30)] = 0
    policy_rate_delta_pp: Annotated[float, Field(ge=-20, le=20)] = 0
    fx_depreciation_pct: Annotated[float, Field(ge=-50, le=100)] = 0
    revenue_gdp_beta: Annotated[float, Field(ge=0, le=5)] = 1
    pricing_pass_through: Fraction = 0.5
    import_cost_share: Fraction = 0.2
    rate_pass_through: Fraction = 0.5
    source: Evidence


def macro_case(case: Case, shock: MacroShock):
    payload = case.model_dump()
    d = payload["drivers"]
    growth_delta = (
        shock.real_growth_delta_pp * shock.revenue_gdp_beta
        + shock.inflation_delta_pp * shock.pricing_pass_through
    ) / 100
    margin_delta = -shock.import_cost_share * shock.fx_depreciation_pct / 100
    rate_delta = shock.policy_rate_delta_pp * shock.rate_pass_through / 100
    d["revenue_growth"] += growth_delta
    d["ebitda_margin"] += margin_delta
    d["wacc"] += rate_delta
    d["borrowing_rate"] += rate_delta
    d["source"] = (d["source"] + " | Macro: " + shock.source)[:1000]
    adjusted = Case.model_validate(payload)
    return dict(
        transmission=dict(
            revenue_growth_delta=growth_delta,
            margin_delta=margin_delta,
            rate_delta=rate_delta,
        ),
        result=value(adjusted),
        assumptions="Analyst-specified linear elasticities; permanent horizon shifts. No estimated causality or automatic terminal inflation adjustment.",
    )


class Simulation(Input):
    draws: Annotated[int, Field(ge=100, le=5000)] = 1000
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)] = 42
    growth_sd: Annotated[float, Field(ge=0, le=0.25)] = 0.025
    margin_sd: Annotated[float, Field(ge=0, le=0.25)] = 0.02
    wacc_sd: Annotated[float, Field(ge=0, le=0.2)] = 0.01
    correlation: list[list[float]] = Field(
        default_factory=lambda: [[1, 0.35, -0.2], [0.35, 1, -0.25], [-0.2, -0.25, 1]]
    )
    reference_price: Annotated[float, Field(gt=0, le=1e12)] | None = None
    source: Evidence = "Illustrative distributions; not empirically calibrated"

    @model_validator(mode="after")
    def matrix(self):
        a = np.asarray(self.correlation)
        if (
            a.shape != (3, 3)
            or not np.isfinite(a).all()
            or not np.allclose(a, a.T, atol=1e-10, rtol=0)
        ):
            raise ValueError("Correlation must be a finite symmetric 3 by 3 matrix")
        if (
            not np.allclose(np.diag(a), 1)
            or (np.abs(a) > 1).any()
            or np.linalg.eigvalsh(a).min() < -1e-10
        ):
            raise ValueError(
                "Correlation must have unit diagonal and be positive semidefinite"
            )
        return self


def simulate(case: Case, settings: Simulation):
    rng = np.random.default_rng(settings.seed)
    shocks = rng.multivariate_normal(
        [0, 0, 0], np.asarray(settings.correlation), settings.draws
    )
    values, forecasts, rejected, failures = [], [], 0, 0
    for z in shocks:
        data = case.model_dump()
        for key, sd, shock in zip(
            ("revenue_growth", "ebitda_margin", "wacc"),
            (settings.growth_sd, settings.margin_sd, settings.wacc_sd),
            z,
        ):
            data["drivers"][key] += float(sd * shock)
        try:
            sample = Case.model_validate(data)
        except ValidationError:
            rejected += 1
            continue
        rows = project(sample, [])
        result = dcf(
            sample,
            rows,
            sample.drivers.wacc,
            sample.drivers.terminal_growth,
            rows[-1]["ebit"],
        )
        if result["status"] != "ok":
            rejected += 1
            continue
        values.append(result["per_share"])
        forecasts.append([r["fcff"] for r in rows])
        failures += any(r["cash"] < 0 for r in rows)
    common = dict(
        requested=settings.draws,
        accepted=len(values),
        rejected=rejected,
        seed=settings.seed,
        numpy_version=np.__version__,
        bit_generator=type(rng.bit_generator).__name__,
        rejection_rate=rejected / settings.draws,
        settings=settings.model_dump(),
        methodology="Correlated normal parameter draws held constant across forecast years; base case only. Invalid/unsupported draws are excluded, never clipped. Statistics are conditional on acceptance.",
    )
    if not values:
        return dict(status="unsupported", **common, reason="No admissible simulations")
    a = np.array(values)
    counts, edges = np.histogram(a, bins=24)
    tail_n = max(1, ceil(0.05 * len(a)))
    fan = np.quantile(np.array(forecasts), [0.05, 0.5, 0.95], axis=0)
    price = settings.reference_price
    losses = np.sort(price - a)[::-1] if price is not None else None
    return dict(
        status="ok",
        **common,
        mean=float(a.mean()),
        std=float(a.std(ddof=1)) if len(a) > 1 else 0,
        p05=float(np.quantile(a, 0.05)),
        p50=float(np.quantile(a, 0.5)),
        p95=float(np.quantile(a, 0.95)),
        lower_tail_mean=float(np.sort(a)[:tail_n].mean()),
        probability_below_price=float((a < price).mean())
        if price is not None
        else None,
        loss_var95=float(np.quantile(price - a, 0.95)) if price is not None else None,
        loss_expected_shortfall95=float(losses[:tail_n].mean())
        if losses is not None
        else None,
        financing_gap_probability=failures / len(a),
        histogram=[
            dict(low=float(edges[i]), high=float(edges[i + 1]), count=int(n))
            for i, n in enumerate(counts)
        ],
        fan=[
            dict(
                year=i + 1,
                p05=float(fan[0, i]),
                p50=float(fan[1, i]),
                p95=float(fan[2, i]),
            )
            for i in range(case.years)
        ],
    )


def diagnostics(case: Case):
    result = value(case)
    base_value = result["base"].get("per_share")
    tornado = []
    for key, delta in [
        ("revenue_growth", 0.01),
        ("ebitda_margin", 0.01),
        ("capex_rate", 0.01),
        ("wacc", 0.01),
        ("terminal_growth", 0.005),
        ("terminal_roic", 0.01),
    ]:
        vals = []
        for sign in (-1, 1):
            payload = case.model_dump()
            payload["drivers"][key] += sign * delta
            try:
                vals.append(
                    value(Case.model_validate(payload))["base"].get("per_share")
                )
            except ValidationError:
                vals.append(None)
        tornado.append(
            dict(
                driver=key,
                shock_pp=delta * 100,
                low_input_value=vals[0],
                high_input_value=vals[1],
            )
        )
    ratios = []
    capital = (
        case.opening.ppe
        + case.opening.receivables
        + case.opening.inventory
        - case.opening.payables
    )
    for r in result["statements"]:
        nopat = r["ebit"] - max(r["ebit"], 0) * case.drivers.tax_rate
        ratios.append(
            dict(
                year=r["year"],
                invested_capital_open=capital,
                roic=nopat / capital if capital > 0 else None,
                economic_profit=nopat - case.drivers.wacc * capital
                if capital > 0
                else None,
                interest_coverage=r["ebit"] / r["interest"]
                if r["interest"] > 0
                else None,
                net_debt_ebitda=(r["debt"] - r["cash"]) / r["ebitda"]
                if r["ebitda"] > 0
                else None,
                fcff_margin=r["fcff"] / r["revenue"] if r["revenue"] else None,
            )
        )
        capital = r["ppe"] + r["receivables"] + r["inventory"] - r["payables"]
    peers = [
        dict(
            name=p.name,
            multiple=p.enterprise_value / p.forward_ebitda
            if p.enterprise_value > 0 and p.forward_ebitda >= 0.01
            else None,
            source=p.source,
            eligible=p.enterprise_value > 0 and p.forward_ebitda >= 0.01,
        )
        for p in case.peers
    ]
    multiples = [p["multiple"] for p in peers if p["eligible"]]
    return dict(
        base_per_share=base_value,
        tornado=tornado,
        ratios=ratios,
        peers=peers,
        peer_quartiles=[float(x) for x in np.quantile(multiples, [0.25, 0.5, 0.75])]
        if multiples
        else [],
        terminal_reinvestment_rate=case.drivers.terminal_growth
        / case.drivers.terminal_roic,
        terminal_value_share=result["base"].get("terminal_pv", 0)
        / result["base"]["enterprise_value"]
        if result["base"].get("enterprise_value", 0) > 0
        else None,
        economic_profit_convention="NOPAT less WACC times opening operating invested capital; excess cash excluded",
    )
