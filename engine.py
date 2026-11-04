"""Annual FCFF valuation for operating companies."""
from datetime import date
from hashlib import sha256
from statistics import median
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Amount = Annotated[float, Field(ge=0, le=1e15)]
Signed = Annotated[float, Field(ge=-1e15, le=1e15)]
Fraction = Annotated[float, Field(ge=0, le=1)]
Rate = Annotated[float, Field(ge=-0.95, le=3)]
Evidence = Annotated[str, Field(min_length=1, max_length=1000)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Opening(Input):
    revenue: Amount
    cash: Amount
    excess_cash: Amount
    receivables: Amount
    inventory: Amount
    ppe: Amount
    payables: Amount
    debt: Amount
    equity: Signed
    diluted_shares: Annotated[float, Field(ge=1, le=1e15)]
    source: Evidence

    @model_validator(mode="after")
    def reconcile(self):
        assets = self.cash + self.receivables + self.inventory + self.ppe
        funding = self.payables + self.debt + self.equity
        if abs(assets - funding) > max(.01, assets * 1e-12):
            raise ValueError("Opening balance sheet does not balance")
        if self.excess_cash > self.cash:
            raise ValueError("Excess cash exceeds opening cash")
        return self


class Drivers(Input):
    revenue_growth: Rate
    ebitda_margin: Rate
    depreciation_rate: Fraction
    capex_rate: Fraction
    receivables_rate: Fraction
    inventory_rate: Fraction
    payables_rate: Fraction
    tax_rate: Fraction
    borrowing_rate: Fraction
    wacc: Annotated[float, Field(gt=0, le=1)]
    terminal_growth: Annotated[float, Field(ge=-.2, le=.25)]
    terminal_roic: Annotated[float, Field(gt=0, le=2)]
    source: Evidence

    @model_validator(mode="after")
    def terminal_constraints(self):
        if self.wacc - self.terminal_growth < .001:
            raise ValueError("WACC must exceed terminal growth by at least 10 basis points")
        if self.terminal_growth >= self.terminal_roic:
            raise ValueError("Terminal growth must be below terminal ROIC")
        return self


class Peer(Input):
    name: Evidence
    enterprise_value: Amount
    forward_ebitda: Signed
    source: Evidence


class Risk(Input):
    factor: Literal["environmental", "social", "governance", "macro"]
    issue: Evidence
    source: Evidence
    confidence: Literal["low", "medium", "high"]
    start: Annotated[int, Field(ge=1, le=10)]
    end: Annotated[int, Field(ge=1, le=10)]
    driver: Literal["revenue_growth", "ebitda_margin", "capex_rate"]
    change_pp: Annotated[float, Field(ge=-50, le=50)]


class Case(Input):
    company: Annotated[str, Field(min_length=1, max_length=100)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    valuation_date: date
    years: Annotated[int, Field(ge=1, le=10)] = 5
    opening: Opening
    drivers: Drivers
    peers: Annotated[list[Peer], Field(max_length=50)] = Field(default_factory=list)
    risks: Annotated[list[Risk], Field(max_length=30)] = Field(default_factory=list)

    @model_validator(mode="after")
    def scenario_bounds(self):
        if any(not risk.start <= risk.end <= self.years for risk in self.risks):
            raise ValueError("Risk years must be ordered and within forecast")
        for year in range(1, self.years + 1):
            growth, margin, capex = effective_drivers(self, self.risks, year)
            if not (-.95 <= growth <= 3 and -.95 <= margin <= 3 and 0 <= capex <= 1):
                raise ValueError(f"Combined scenario assumptions exceed bounds in year {year}")
        return self


def effective_drivers(case, risks, year):
    values = []
    for driver in ("revenue_growth", "ebitda_margin", "capex_rate"):
        shift = sum(r.change_pp for r in risks if r.driver == driver and r.start <= year <= r.end)
        values.append(getattr(case.drivers, driver) + shift / 100)
    return values


def project(case, risks):
    d, o = case.drivers, case.opening
    revenue, cash, ppe, equity = o.revenue, o.cash, o.ppe, o.equity
    previous_nwc = o.receivables + o.inventory - o.payables
    rows = []
    for year in range(1, case.years + 1):
        growth, margin, capex_rate = effective_drivers(case, risks, year)
        revenue *= 1 + growth
        ebitda, capex = revenue * margin, revenue * capex_rate
        depreciation = min(revenue * d.depreciation_rate, ppe + capex)
        ppe += capex - depreciation
        ebit = ebitda - depreciation
        interest = o.debt * d.borrowing_rate
        pretax = ebit - interest
        tax = max(pretax, 0) * d.tax_rate
        net_income = pretax - tax
        equity += net_income
        receivables = revenue * d.receivables_rate
        inventory = revenue * d.inventory_rate
        payables = revenue * d.payables_rate
        nwc = receivables + inventory - payables
        change_nwc = nwc - previous_nwc
        previous_nwc = nwc
        cfo = net_income + depreciation - change_nwc
        change_cash = cfo - capex
        cash += change_cash
        nopat = ebit - max(ebit, 0) * d.tax_rate
        rows.append(dict(year=year, revenue=revenue, ebitda=ebitda, depreciation=depreciation,
                         ebit=ebit, interest=interest, pretax=pretax, tax=tax, net_income=net_income,
                         cfo=cfo, cfi=-capex, cff=0, change_cash=change_cash, cash=cash,
                         receivables=receivables, inventory=inventory, ppe=ppe, payables=payables,
                         debt=o.debt, equity=equity, change_nwc=change_nwc,
                         assets=cash+receivables+inventory+ppe, funding=payables+o.debt+equity,
                         fcff=nopat+depreciation-capex-change_nwc))
    return rows


def bridge(case, ev):
    equity = ev + case.opening.excess_cash - case.opening.debt
    return dict(enterprise_value=ev, equity_value=equity, per_share=equity/case.opening.diluted_shares)


def dcf(case, rows, wacc, growth, terminal_ebit):
    explicit = sum(r["fcff"] / (1 + wacc) ** r["year"] for r in rows)
    if terminal_ebit <= 0:
        return dict(status="unsupported", reason="Normalized terminal EBIT is non-positive", explicit_pv=explicit)
    terminal_nopat = terminal_ebit * (1-case.drivers.tax_rate) * (1+growth)
    terminal_fcff = terminal_nopat * (1-growth/case.drivers.terminal_roic)
    terminal_pv = terminal_fcff / (wacc-growth) / (1+wacc)**case.years
    return dict(status="ok", explicit_pv=explicit, terminal_pv=terminal_pv, terminal_fcff=terminal_fcff,
                **bridge(case, explicit+terminal_pv))


def value(case: Case) -> dict:
    d = case.drivers
    base = project(case, [])
    scenario = project(case, case.risks)
    terminal_ebit = base[-1]["ebit"]
    # Explicit margin and capex shocks expire. Revenue level effects persist.
    scenario_ebit = terminal_ebit * scenario[-1]["revenue"]/base[-1]["revenue"] if base[-1]["revenue"] else 0
    central = dcf(case, base, d.wacc, d.terminal_growth, terminal_ebit)
    stressed = dcf(case, scenario, d.wacc, d.terminal_growth, scenario_ebit)
    sensitivity = []
    for wacc_shift in (-.02, -.01, 0, .01, .02):
        for growth_shift in (-.01, 0, .01):
            wacc, growth = d.wacc+wacc_shift, d.terminal_growth+growth_shift
            valid = 0 < wacc <= 1 and -.2 <= growth <= .25 and wacc-growth >= .001 and growth < d.terminal_roic
            result = dcf(case, base, wacc, growth, terminal_ebit) if valid else {}
            sensitivity.append(dict(wacc=wacc, growth=growth, per_share=result.get("per_share")))
    eligible = [p.enterprise_value/p.forward_ebitda for p in case.peers
                if p.enterprise_value > 0 and p.forward_ebitda >= .01]
    multiple = median(eligible) if eligible else None
    comps = dict(eligible=len(eligible), median_ev_ebitda=multiple)
    if multiple is not None and base[0]["ebitda"] > 0:
        comps.update(bridge(case, multiple*base[0]["ebitda"]))
    checks = []
    for name, rows in (("Base", base), ("Scenario", scenario)):
        for row in rows:
            if abs(row["assets"]-row["funding"]) > max(.02, abs(row["assets"])*1e-10):
                checks.append(f"{name} year {row['year']}: balance sheet mismatch")
            if row["cash"] < 0:
                checks.append(f"{name} year {row['year']}: financing shortfall {-row['cash']:,.2f}")
    if central.get("enterprise_value", 0) > 0 and central["terminal_pv"]/central["enterprise_value"] > .75:
        checks.append("Terminal value exceeds 75% of enterprise value")
    if len(eligible) < 3:
        checks.append("Fewer than three eligible peers")
    return dict(version="0.1.0", input_sha256=sha256(case.model_dump_json().encode()).hexdigest(),
                inputs=case.model_dump(mode="json"), base=central, scenario=stressed, comps=comps,
                statements=base, scenario_statements=scenario, sensitivity=sensitivity, checks=checks)
