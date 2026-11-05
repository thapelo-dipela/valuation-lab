# Architecture and model contracts

## Runtime boundaries

`engine.py` owns the linked operating-company forecast and FCFF model. `advanced.py` owns capital cost, explicit cash-flow methods, survival PV, macro scenarios, diagnostics and simulations. `research_engine.py` owns expectations and review logic. `forecasting.py` is a separate experimental price-model evaluation layer. `providers.py` and `instruments.py` retrieve and normalize external observations without automatically filling valuation inputs.

FastAPI and MCP expose the same functions. The browser renders returned figures; it does not independently recalculate financial results. Case editing marks old results stale, and simulation-setting changes require a rerun before saving a simulation.

## Storage

SQLite is initialized from `data/schema.sql`; `VALUATION_DB` can override its local path. Source and skill catalogs are seeded from version-controlled JSON. Runs contain normalized inputs, deterministic outputs, optional simulation settings/results, input and payload hashes, and a knowledge-catalog hash. SQL triggers prevent normal run updates/deletion. This is an audit aid, not tamper-proof storage against someone with filesystem access.

Evidence attaches to a saved run. Records preserve input mapping, claim, source URL, publication/retrieval dates, period, units, locator, kind and review state. Provider snapshots and instrument import manifests preserve retrieval provenance. Future-published evidence cannot satisfy historical review gates.

## Calculation conventions

- Full monetary units, annual decimal rates and end-year discounting.
- FCFF operating tax excludes loss carryforwards. Linked statements use fixed debt, no new financing/distributions and simplified working capital.
- Terminal reinvestment is `growth / ROIC`; terminal EBIT must be positive. Margin/capex risk shocks expire; revenue-level effects persist.
- Equity bridge includes excess cash, additional non-operating asset values, gross debt and other claims. Additional bridge values do not alter the simplified operating balance sheet; avoid double counting.
- Generic FCFE/dividend/APV/residual-income calculators require explicitly prepared cash flows. They do not construct a full financing or clean-surplus schedule automatically.
- Simulation samples constant growth/margin/WACC parameters; it is not a stochastic year-to-year economy or insurance capital model. Rejected draws are excluded and disclosed. Tail metrics are conditional on accepted draws.
- Reverse DCF scans a bounded grid then bisects sign changes. No bracket produces an explicit no-solution state. Tangent roots or roots between unresolved grid features may be missed.
- Scenario weights are analyst supplied and require consistent company/currency/date/share basis. Unsupported positive-weight scenarios block aggregation.

## Research workflow

The seven-role plan is a deterministic task specification, not evidence that seven AI agents ran. An MCP client may assign the work to its own models: retrieve relevant skills, gather dated sources, call calculations, present competing arguments, challenge the tails, and synthesize only supported conclusions. Missing evidence and conflicting claims remain visible. No broker execution is included.

## Deployment boundary

Run on loopback for local single-user research. The application has no authentication, tenancy, network rate limits or hosted secrets service. Do not expose the raw development server publicly without implementing those controls and completing a deployment review. Numeric/API validation and bounded provider requests are implemented; they do not replace production access controls.

## Extending safely

Add a typed input, deterministic function, known-answer tests, method card, source provenance and API/MCP route for every new numerical method. Add providers behind explicit query/normalization contracts. Preserve old model versions and frozen datasets when introducing migrations or calibrated models. The checked-in SQL schema currently has one initial version; future breaking changes need explicit migrations.
