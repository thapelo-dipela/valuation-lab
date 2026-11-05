# Research brief: a CFA-oriented multidisciplinary valuation workbench

Research date: 4 November 2026. Scope: investment analysis and deterministic modeling, not a reproduction of a professional curriculum or a claim of professional accreditation.

## Executive summary

The original repository contained a single FCFF model, a basic HTML form and a research link table. It lacked persistent evidence, method selection, uncertainty analysis and calculation regression tests. The upgraded architecture gives each discipline a method catalog, executable calculations where appropriate, explicit review-only procedures, and reusable analyst instructions. CFA investment analysis is the organizing framework; CFP suitability remains a separate client-decision layer.

The research approach was source-grounded: define questions, search varied terms, open publisher pages, assess authority and applicability, and preserve unresolved limitations. It follows NotebookLM-style evidence discipline but does not connect to NotebookLM, ingest its notebooks, or train a model. Thirteen primary publisher sources were opened. Original summaries and method cards are redistributed; licensed books and curriculum text are not.

## Research questions and search coverage

1. **What belongs in a defensible valuation engine?** Queries covered CFA FCFF/FCFE, residual income, valuation process/model selection, Damodaran cost of capital, and APV. CFA and NYU independently support matching methods to cash-flow characteristics and distinguishing enterprise from equity claims.
2. **How should economic data and uncertainty enter a valuation?** Queries covered World Bank indicators, IMF SDMX, SARB time series, SEC XBRL, ASOP 56 modeling, and expected shortfall. Official statistical and filing sources describe access and metadata; ASOP 56 provides model-governance principles. Data availability does not establish company-specific elasticities or distribution calibration.
3. **How should users investigate and communicate the result?** Queries covered CFA valuation reporting, W3C complex chart accessibility, Vega-Lite selections, and FPSB practice standards. These support inspectable assumptions, interactive exploration, text alternatives and separation of valuation from client suitability.

## Key findings and implementation decisions

### Valuation and capital allocation

CFA Institute (2026a, 2026b, 2026c) distinguishes cash-flow and accounting-based equity methods and emphasizes an explicit valuation process. Damodaran (n.d.) provides an independent valuation perspective. The engine therefore keeps FCFF, FCFE, dividends, residual income and APV separate. Their outputs are not automatically averaged. Residual-income inputs must satisfy clean-surplus assumptions; APV requires explicit tax shields. These are original implementation decisions based on the sources, not assertions that every feature is curriculum-complete.

The terminal FCFF calculation retains growth-dependent reinvestment. Capital-cost construction exposes the unlevered beta, target leverage, equity premium, country exposure and tax assumptions. NYU's January 2026 US industry table is a benchmark source, not a ZAR rate feed. [CFA free cash flow valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation), [CFA residual income](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/residual-income-valuation), [NYU valuation](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/background/valintro.htm), [NYU cost of capital](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html).

### Economist and data-analyst workflow

World Bank, IMF and SARB provide official macroeconomic access points. Their series require careful treatment of units, frequency and publication vintage. The shipped World Bank adapter retrieves three selected series and stores source provenance; IMF and SARB remain cataloged sources requiring dedicated adapters. A current historical observation is not a historical release vintage. The application explicitly avoids claiming point-in-time macro data.

SEC companyfacts provides structured filing observations. A separate ingestion CLI preserves its response; a selector filters filing dates and exact accounting contexts. Neither adapter automatically converts observations into a company forecast. Macro transmission is an analyst-specified scenario with visible coefficients, not an econometrically estimated causal model. [World Bank API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392), [IMF APIs](https://data.imf.org/en/Resource-Pages/IMF-API), [SARB statistics](https://www.resbank.co.za/en/home/what-we-do/statistics/releases/online-statistical-query), [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

### Actuarial uncertainty and model governance

ASOP 56 (Actuarial Standards Board, 2019) is a primary modeling-governance reference. It is a US standard; the workbench does not claim compliance with South African actuarial or insurance regulation. The simulation records its seed, dependence matrix, rejected draws and accepted-sample statistics. Normal parameter shocks are an implementation choice, not a calibrated distribution. Survival-contingent PV and curve sensitivity are limited mathematical calculators, not an insurance reserving system. No source is cited as validating the fictional example calibration. [ASOP 56](https://www.actuarialstandardsboard.org/asops/modeling-3/).

### Visual reasoning and suitability

W3C's chart guidance supports text alternatives; Vega-Lite documents interactive selections. The frontend implements native SVG with exact data tables, scenario controls and sensitivity-cell selection. It does not depend on Vega-Lite. FPSB supports a distinct planning process: a company's estimated value does not establish suitability for a client. [W3C complex images](https://www.w3.org/WAI/tutorials/images/complex/), [Vega-Lite selection parameters](https://vega.github.io/vega-lite/docs/selection.html), [FPSB standards](https://fpsb.org/standards-for-the-profession/).

## Source reliability and authenticity

All thirteen sources are hosted by the issuing institution or original author. CFA and NYU are educational/analytical sources; SEC, World Bank, IMF and SARB are provider documentation; ASB and FPSB are professional standards publishers; W3C and Vega are technical publishers. Each source has a contribution, date where published, accessed date, authority classification and rights note in `data/knowledge.json`. Undated dynamic documentation is labeled undated rather than assigned a fabricated publication date. Marketing and curriculum access incentives exist on professional-body websites; no source's credential claims are treated as evidence of software correctness.

The Basel expected-shortfall search was exploratory; it is not used to claim Basel compliance or to calibrate the empirical loss estimator. No legal or regulatory advice is derived from an undated page. Numerical formulas are checked through independent hand calculations and invariants in tests, not by citations alone.

## Conflicts, gaps and uncertainties

- Model rankings depend on business type, capital structure and accounting quality. Differences among methods are not automatically errors.
- CFA and CFP knowledge are complementary but serve different decisions. CFA remains the investment-analysis core.
- Source availability is not a redistribution license. Full licensed databases, curriculum books and paywalled market feeds have not been copied.
- No trained reasoning model or autonomous research agent is embedded. MCP clients can retrieve the skills and call deterministic tools with their own language model.
- The example is fictional. No observed market rates, survival table or macro coefficient has been silently adopted as a default.
- Missing capabilities include bank/insurer valuation, tax-loss carryforwards, dynamic debt schedules, full LBO and merger models, option pricing, portfolio optimization, historical-vintage macro feeds, empirical risk calibration and multi-user access control.
- Broad professional knowledge is not exhausted by 30 method cards. The catalog is versioned and extensible; implementation status is visible for each method.

## References

Actuarial Standards Board. (2019, December). *ASOP No. 56: Modeling*. https://www.actuarialstandardsboard.org/asops/modeling-3/

CFA Institute. (2026a). *Equity valuation: Applications and processes*. https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-applications-and-processes

CFA Institute. (2026b). *Free cash flow valuation*. https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation

CFA Institute. (2026c). *Residual income valuation*. https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/residual-income-valuation

Damodaran, A. (n.d.). *An introduction to valuation*. NYU Stern. https://pages.stern.nyu.edu/~adamodar/New_Home_Page/background/valintro.htm

Damodaran, A. (2026, January). *Cost of equity and capital (US)*. NYU Stern. https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html

Financial Planning Standards Board. (n.d.). *Standards for the profession*. https://fpsb.org/standards-for-the-profession/

International Monetary Fund. (n.d.). *IMF data APIs*. https://data.imf.org/en/Resource-Pages/IMF-API

South African Reserve Bank. (n.d.). *Online statistical query*. https://www.resbank.co.za/en/home/what-we-do/statistics/releases/online-statistical-query

U.S. Securities and Exchange Commission. (2024, June 6). *EDGAR application programming interfaces*. https://www.sec.gov/search-filings/edgar-application-programming-interfaces

Vega-Lite maintainers. (n.d.). *Selection parameters*. https://vega.github.io/vega-lite/docs/selection.html

World Bank. (n.d.). *About the indicators API documentation*. https://datahelpdesk.worldbank.org/knowledgebase/articles/889392

World Wide Web Consortium. (n.d.). *Complex images*. Web Accessibility Initiative. https://www.w3.org/WAI/tutorials/images/complex/

All web references retrieved 4 November 2026.
