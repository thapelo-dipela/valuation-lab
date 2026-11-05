"""Explicit, bounded public-data adapters. No automatic valuation input mapping."""

from datetime import datetime, timezone, date
from hashlib import sha256
import json
import re
import httpx


def fetch_json(url, user_agent="ValuationLab/0.2 research workbench"):
    with httpx.Client(
        timeout=20,
        follow_redirects=False,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    ) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            parts = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 20_000_000:
                    raise ValueError(
                        "Provider response exceeds 20 MB; use a narrower query"
                    )
                parts.append(chunk)
    raw = b"".join(parts)
    return dict(
        url=url,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        sha256=sha256(raw).hexdigest(),
        data=json.loads(raw),
    )


INDICATORS = {
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "inflation": "FP.CPI.TOTL.ZG",
    "real_gdp": "NY.GDP.MKTP.KD",
}


def world_bank(country="ZAF", indicator="gdp_growth", start=2015, end=2025):
    if (
        not re.fullmatch(r"[A-Z]{3}", country)
        or indicator not in INDICATORS
        or not 1960 <= start <= end <= 2100
        or end - start > 60
    ):
        raise ValueError(
            "Use a three-letter country, supported indicator and ordered range of up to 60 years"
        )
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{INDICATORS[indicator]}?format=json&date={start}:{end}&per_page=100"
    packet = fetch_json(url)
    raw = packet.pop("data")
    if (
        not isinstance(raw, list)
        or len(raw) != 2
        or not isinstance(raw[0], dict)
        or not isinstance(raw[1], list)
    ):
        raise ValueError("World Bank returned no usable observations")
    observations = [
        dict(
            year=r["date"],
            value=r["value"],
            country=r.get("countryiso3code", country),
            unit="annual percent"
            if indicator != "real_gdp"
            else "constant USD (provider base year)",
        )
        for r in raw[1]
    ]
    return dict(
        **packet,
        provider="World Bank",
        indicator=INDICATORS[indicator],
        metadata=raw[0],
        observations=observations,
        vintage_warning="Current-release snapshot, not point-in-time vintage data. Never use observation year as publication date.",
    )


def company_facts(cik, contact):
    if (
        not re.fullmatch(r"\d{1,10}", cik)
        or "@" not in contact
        or len(contact) > 150
        or any(ord(c) < 32 for c in contact)
    ):
        raise ValueError(
            "SEC requires a numeric CIK and a contact email in the User-Agent"
        )
    return fetch_json(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json",
        f"ValuationLab research {contact}",
    )


def select_company_fact(payload, taxonomy, concept, unit, as_of):
    cutoff = date.fromisoformat(as_of)
    records = (
        payload.get("facts", {})
        .get(taxonomy, {})
        .get(concept, {})
        .get("units", {})
        .get(unit, [])
    )
    selected = {}
    conflicts = []
    for r in records:
        if not r.get("filed") or date.fromisoformat(r["filed"]) > cutoff:
            continue
        key = (r.get("start"), r.get("end"))
        old = selected.get(key)
        if old and old["filed"] == r["filed"] and old.get("val") != r.get("val"):
            conflicts.append(dict(period=key, first=old, second=r))
        if not old or r["filed"] > old["filed"]:
            selected[key] = r
    return dict(
        taxonomy=taxonomy,
        concept=concept,
        unit=unit,
        as_of=as_of,
        observations=sorted(
            selected.values(), key=lambda r: (r.get("end", ""), r.get("start", ""))
        ),
        conflicts=conflicts,
        mapping_status="Unmapped; analyst must reconcile accounting perimeter and period",
    )
