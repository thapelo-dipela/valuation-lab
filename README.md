# Valuation Lab

Apache-2.0 valuation workbench for operating businesses. One deterministic engine powers the dashboard, REST API and local MCP server.

## Run

Requires Python 3.11 or later.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and run the fictional case. Edit or upload case JSON. All monetary inputs use full currency units. Annual rates are decimals, and scenario changes use percentage points. API documentation is at /docs. POST the case to /api/v1/valuation or /api/v1/export/docx, /xlsx or /pptx under the same export route. Excel contains generated forecast values. Modify and rerun the case to recalculate.

For MCP, use your environment's Python interpreter with the absolute path to mcp_server.py. Connect over stdio and call valuation_input_schema and run_valuation. Read the [reasoning skill](skills/valuation-reasoning/SKILL.md) via valuation://skills/reasoning. The client supplies the AI model.

## Model assumptions

- End-of-year FCFF uses EBIT after operating cash taxes, plus depreciation, less capex and the increase in operating working capital. There are no tax-loss carryforwards.
- Terminal FCFF uses next-year normalized NOPAT times one minus terminal growth divided by terminal ROIC. Non-positive terminal EBIT makes the perpetuity estimate unavailable.
- The equity bridge adds analyst-specified excess cash and subtracts gross debt. Other claims and non-operating assets are outside the current model.
- Forward EV/EBITDA uses the median of eligible supplied peers and year-one subject EBITDA. Align accounting and time periods.
- Scenario margin and capex shocks expire at the horizon. Scenario revenue-level changes persist in terminal EBIT.
- Forecasts assume fixed debt, no distributions or new financing and a simplified operating balance sheet. Negative cash flags a financing gap.

Local, in-memory prototype. Model checks and management forecasts are preliminary. Live ingestion, assurance, professional valuation opinions and insurance liability models require additional work. See the [research map](docs/research.md).
