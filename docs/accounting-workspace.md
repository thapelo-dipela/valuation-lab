# Accounting workspace and usage boundaries

The interface uses familiar dark repository navigation, built with original HTML, CSS and SVG. It does not use GitHub logos, brand assets or imply affiliation. See [GitHub trademark policy](https://docs.github.com/en/site-policy/content-removal-policies/github-trademark-policy).

Historical statement and price examples are fictional. Importing a CSV does not establish permission to redistribute the underlying data. This build does not scrape commercial price feeds or bundle proprietary CFA curriculum. Existing repository licenses and FinanceDatabase attribution remain in THIRD_PARTY_NOTICES.md.

Currency rates come from ECB via Frankfurter, restricted to the ECB provider. [Frankfurter documentation](https://frankfurter.dev/) describes the dated API. The interface retains reporting amounts and uses a single dated rate for display comparisons, not IAS 21 translation, executable FX quotes or historical-period translation. ZAC and GBX share quotes are normalized to ZAR and GBP before comparison. Cross-currency price comparisons without a matching financial reporting currency are disabled.

ECB reference data is available free from the [ECB](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html). Converted amounts are application calculations. [ECB reuse conditions](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html) require attribution, accurate reproduction, identification of modifications and disclosure of free availability when incorporated into sold documents. The app attributes returned rates; monetized redistribution needs those disclosures in its purchasing and delivery flows.

This is a local analytical application, not a licensed advice or execution service. Legal requirements for a commercial launch depend on jurisdictions, data agreements and actual features. No guarantee of universal legal compliance is made.

## Calculation contracts
- Financial statements use whole reporting-currency amounts, annual periods and supplied CFO. Balance sheets must reconcile. No artificial current ratio is calculated without short-term borrowing classifications. First-year average-balance ratios are unavailable.
- Saving statements writes a versioned snapshot to the local SQLite database; browser local storage restores the most recently saved statement draft. Valuation runs remain separate immutable records.
- Statement CSV columns are available via Download CSV. Numeric values must be unformatted; periods must be unique and ascending. Imported records are user data, not independently verified evidence.
- Annual operating schedules drive revenue, operating margins, depreciation, capex, working capital, tax and interest. Global WACC and terminal growth/ROIC remain terminal assumptions. Debt is fixed and no dividend/new-financing schedule is inferred. Macro and simulation operating shocks apply to every scheduled year; reverse DCF solves a constant operating assumption across years.
- Share models include FCFF DCF, EV/EBITDA peers, historical P/E, book multiples and Gordon dividends. Unsupported earnings/book/growth cases show no value. Price returns exclude dividends; no total-return claim is made.
- Display conversion is limited to the Financials and Share price surfaces. Other views and exports explicitly retain case/source currency.
