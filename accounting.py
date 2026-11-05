"""Annual statement analysis. Source amounts remain in their reporting currency."""

from datetime import date
from typing import Annotated
import math
from pydantic import Field, model_validator
from engine import Input, Amount, Signed, Evidence
from providers import fetch_json


class Period(Input):
    year: Annotated[int, Field(ge=1900, le=2100)]
    revenue: Amount
    cost_of_sales: Amount
    operating_expenses: Amount
    depreciation: Amount
    interest: Amount
    tax: Amount
    cash: Amount
    receivables: Amount
    inventory: Amount
    ppe: Amount
    payables: Amount
    debt: Amount
    equity: Signed
    cfo: Signed
    capex: Amount
    diluted_shares: Annotated[float, Field(gt=0, le=1e15)]

    @model_validator(mode="after")
    def balanced(self):
        assets = self.cash + self.receivables + self.inventory + self.ppe
        if abs(assets - self.payables - self.debt - self.equity) > max(
            0.01, assets * 1e-9
        ):
            raise ValueError(f"{self.year}: assets must equal liabilities plus equity")
        return self


class Accounts(Input):
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    source: Evidence
    periods: Annotated[list[Period], Field(min_length=1, max_length=30)]

    @model_validator(mode="after")
    def ordered(self):
        years = [p.year for p in self.periods]
        if years != sorted(set(years)):
            raise ValueError("Years must be unique and ascending")
        return self


def divide(a, b):
    return a / b if b > 0 else None


def analyze(accounts: Accounts):
    rows = []
    previous = None
    for p in accounts.periods:
        r = p.model_dump()
        gross = p.revenue - p.cost_of_sales
        ebitda = gross - p.operating_expenses
        ebit = ebitda - p.depreciation
        ni = ebit - p.interest - p.tax
        assets = p.cash + p.receivables + p.inventory + p.ppe
        avg_assets = (assets + previous["assets"]) / 2 if previous else None
        avg_equity = (p.equity + previous["equity"]) / 2 if previous else None
        avg_ar = (p.receivables + previous["receivables"]) / 2 if previous else None
        avg_inventory = (p.inventory + previous["inventory"]) / 2 if previous else None
        avg_ap = (p.payables + previous["payables"]) / 2 if previous else None
        dso = divide(avg_ar * 365, p.revenue) if previous else None
        dio = divide(avg_inventory * 365, p.cost_of_sales) if previous else None
        dpo = divide(avg_ap * 365, p.cost_of_sales) if previous else None
        r.update(
            gross_profit=gross,
            ebitda=ebitda,
            ebit=ebit,
            net_income=ni,
            assets=assets,
            fcf=p.cfo - p.capex,
            eps=ni / p.diluted_shares,
            gross_margin=divide(gross, p.revenue),
            ebitda_margin=divide(ebitda, p.revenue),
            net_margin=divide(ni, p.revenue),
            roe=divide(ni, avg_equity) if previous else None,
            roa=divide(ni, avg_assets) if previous else None,
            revenue_growth=(p.revenue / previous["revenue"])
            ** (1 / (p.year - previous["year"]))
            - 1
            if previous and previous["revenue"]
            else None,
            cash_conversion=divide(p.cfo, ni),
            interest_coverage=divide(ebit, p.interest),
            net_debt_ebitda=divide(p.debt - p.cash, ebitda),
            dso=dso,
            dio=dio,
            dpo=dpo,
            cash_cycle=dso + dio - dpo
            if all(x is not None for x in (dso, dio, dpo))
            else None,
            accrual_ratio=divide(ni - p.cfo, avg_assets) if previous else None,
        )
        rows.append(r)
        previous = r
    return dict(
        currency=accounts.currency,
        source=accounts.source,
        rows=rows,
        conventions="Annual periods; ROA, ROE and working-capital days use average balances. First-period averages unavailable. Growth is annualized across missing years. CFO is supplied, not inferred. No current ratio without debt maturity data.",
    )


def fx_quote(base: str, quote: str, as_of: date):
    if base == quote:
        return dict(
            base=base,
            quote=quote,
            rate=1,
            date=as_of.isoformat(),
            source="Same currency",
        )
    if as_of > date.today():
        raise ValueError("Choose an exchange-rate date no later than today")
    snapshot = fetch_json(
        f"https://api.frankfurter.dev/v2/rate/{base}/{quote}?date={as_of.isoformat()}&providers=ecb"
    )
    data = snapshot["data"]
    if data.get("base", "").upper() != base or data.get("quote", "").upper() != quote:
        raise ValueError("Currency provider returned a different pair")
    rate = float(data["rate"])
    if not math.isfinite(rate) or rate <= 0 or date.fromisoformat(data["date"]) > as_of:
        raise ValueError("Currency provider returned an invalid rate or date")
    return dict(
        base=base,
        quote=quote,
        rate=rate,
        date=data["date"],
        source="ECB via Frankfurter",
        url=snapshot["url"],
        sha256=snapshot["sha256"],
        retrieved_at=snapshot["retrieved_at"],
    )
