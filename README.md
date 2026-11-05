# Valuation Lab

A CFA-oriented valuation and research workbench with guided and advanced browser views, deterministic financial calculations, a source-linked skills database, and REST/MCP interfaces. CFP suitability remains a separate workflow.

## Start locally

Python 3.11+:

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The initial company is fictional. Monetary inputs use full units; annual rates are decimals in JSON and percentages in the sidebar. Scenario shocks use percentage points.

## Capabilities

- Linked statements, FCFF DCF, normalized terminal reinvestment, peer medians/quartiles, extended equity bridge, sensitivity and driver influence.
- Bottom-up WACC, explicit FCFE/dividend/residual-income/APV calculators, survival-weighted liabilities and curve sensitivity.
- Seeded correlated simulations, percentile bands, funding-gap probability, price-relative downside and expected shortfall.
- Macro transmission, reverse DCF, earnings-quality diagnostics and probability-weighted valuation scenarios.
- Walk-forward random-walk/drift/AR(1) evaluation; optional adapter for a separately loaded Kronos predictor.
- 35 original method cards across ten disciplines, 25 source entries, full discipline SKILL.md workflows and a twelve-repository review catalog.
- Persistent SQLite runs, hashes, source evidence, provider snapshots and searchable security listings.
- Guided/Advanced dashboard with charts, clickable sensitivity cells, risk laboratory, method studio, knowledge/discovery and evidence review.
- Existing Word, Excel and PowerPoint valuation exports; run JSON carries diagnostics and optional simulation. Document exports cover the valuation case, not the entire research database. Excel outputs are calculated values, not a formula-driven replacement engine.

## Import the security universe

```sh
python scripts/ingest_instruments.py
```

This imports the full equities file at a pinned FinanceDatabase commit into local SQLite. The reviewed snapshot contains 121,559 listing records, including duplicate issuers across listings. It is not live price or fundamentals data. Preserve original currencies: ZAC quotes are cents, not ZAR. The dataset is excluded from Git; its MIT notice is included.

The dashboard can also retrieve three official World Bank macro series. SEC companyfacts ingestion is explicit:

```sh
python scripts/ingest_sec.py --cik 320193 --contact you@example.com
```

The SEC adapter requires your actual contact email in its User-Agent. It preserves raw data; analyst-approved concept, unit, filing-date and period mapping remains necessary. World Bank retrieval was live-tested; SEC retrieval was not exercised with a user contact.

## Research and model boundaries

The application provides deterministic specialist review tasks, not an embedded autonomous LLM. MCP clients supply their own models and can retrieve skills, gather evidence, call calculations and challenge the result. No model weights are downloaded, no paid data API is invoked, and no trades are executed by the application.

Kronos concerns market-path forecasts; it does not replace fundamental valuation. Its optional callback has not been validated against installed model weights. Training-data overlap, model calibration, data licensing and empirical performance require separate evaluation.

The core forecast assumes constant annual drivers, fixed debt, no distributions/new financing, no tax-loss carryforwards and a simplified operating balance sheet. Margin/capex shocks expire at the horizon; revenue-level effects persist. Banks, insurers, full LBO/debt schedules, option pricing and regulatory capital models are outside this release. See the complete [model contracts](docs/architecture.md).

## API and MCP

Interactive API schema: `/docs`.

| Route | Purpose |
|---|---|
| `POST /api/v1/analysis` | Case valuation, diagnostics, optional simulation and saved run |
| `POST /api/v1/methods/{capital-cost,cashflows,liability}` | Explicit-input calculators |
| `POST /api/v1/macro` | Macro shock transmission |
| `POST /api/v1/research/{reverse-dcf,earnings-quality,scenarios,plan,forecast-evaluation}` | Research calculations and workflow |
| `GET /api/v1/knowledge` | Method/source search |
| `GET /api/v1/instruments` | Pinned security-master search |
| `GET /api/v1/repositories` | Reviewed code revisions and decisions |
| `GET /api/v1/runs` | Saved calculation history |
| `POST /api/v1/runs/{id}/evidence` | Attach evidence to a saved run |
| `GET /api/v1/data/world-bank` | Official macro observations and stored snapshot |

For MCP, launch `python mcp_server.py` using the environment's Python interpreter and absolute script path. It exposes the same calculators, knowledge retrieval, instrument discovery, forecast evaluation and research planning over stdio. Start with `search_knowledge`, `read_skill`, `valuation_input_schema` and `plan_research`.

## Validation

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/build_knowledge.py
```

Tests cover known-answer valuations, accounting identities, sensitivities, risk distributions, invalid inputs, audit persistence, evidence, API exports, reverse solves, scenario consistency and forecast-cutoff isolation. GitHub Actions runs Python 3.11 and 3.13. Optional browser checks require Playwright/Chromium, a running server and the imported universe:

```sh
python -m pip install playwright
python -m playwright install chromium
# Start server on port 8018, or set VALUATION_URL.
python scripts/browser_smoke.py
```

## Sources and architecture

- [Primary-source research brief](docs/research-brief.md)
- [Twelve-repository study and integration decisions](docs/repository-study.md)
- [Architecture, storage and model contracts](docs/architecture.md)
- [Design system](DESIGN.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

The curated library is extensible; it is not the full licensed CFA or CFP curriculum. The local application is single-user and unauthenticated. Keep it on loopback until production access controls and deployment review are implemented.

## Accounting workspace

Financials now provides editable annual statements, historical revenue/earnings/CFO charts, average-balance ratios and CSV import/export. Forecasts provides annual driver schedules and projected income/balance/cash-flow tables. Share price provides imported OHLCV candles, historical price returns and five comparable per-share methods. Calculators use labelled fields rather than JSON editors. The design follows the requested GitHub-style dark layout.

See [accounting workspace contracts](docs/accounting-workspace.md) for units, currency conversion, evidence and licensing boundaries. New endpoints: POST `/api/v1/accounting`, GET `/api/v1/fx?base=ZAR&quote=USD&as_of=2026-11-04`.
