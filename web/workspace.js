"use strict";
// Accounting workspace: source-currency inputs, explicit display-only translation.
let accounts,
  accountResult,
  fx = { rate: 1 },
  accountView = "income",
  accountEditing = false;
const accountFields = [
  "revenue",
  "cost_of_sales",
  "operating_expenses",
  "depreciation",
  "interest",
  "tax",
  "cash",
  "receivables",
  "inventory",
  "ppe",
  "payables",
  "debt",
  "equity",
  "cfo",
  "capex",
  "diluted_shares",
];
const labels = {
  ppe: "Property, plant & equipment",
  cfo: "Operating cash flow",
  fcf: "Free cash flow",
  eps: "Earnings per share",
  ebit: "Operating profit",
  ebitda: "EBITDA",
  roa: "Return on assets",
  roe: "Return on equity",
  dso: "Receivable days",
  dio: "Inventory days",
  dpo: "Payable days",
  cash_cycle: "Cash conversion cycle",
  net_debt_ebitda: "Net debt / EBITDA",
  revenue_growth: "Revenue growth (annualized)",
  cfi: "Investing cash flow",
  cff: "Financing cash flow",
  fcff: "Free cash flow to firm",
};
const labelOf = (k) =>
  labels[k] || title(k).replace(/^./, (c) => c.toUpperCase());
const ratios = new Set([
  "gross_margin",
  "ebitda_margin",
  "net_margin",
  "roe",
  "roa",
  "revenue_growth",
  "accrual_ratio",
]);
const multiples = new Set([
  "cash_conversion",
  "interest_coverage",
  "net_debt_ebitda",
]);
const days = new Set(["dso", "dio", "dpo", "cash_cycle"]);
const currencyChoices = [
  "ZAR",
  "USD",
  "EUR",
  "GBP",
  "JPY",
  "CHF",
  "CAD",
  "AUD",
  "CNY",
  "INR",
  "BRL",
  "MXN",
  "SGD",
  "HKD",
  "NZD",
];
function section(id, heading) {
  const s = document.createElement("section");
  s.className = "view";
  s.id = id;
  s.hidden = true;
  el(s, "h2", heading);
  by("workspace").insertBefore(s, document.querySelector("footer"));
  return s;
}
function action(parent, text, fn, cls = "") {
  const b = el(parent, "button", text, cls);
  b.type = "button";
  b.onclick = () => guarded(fn);
  return b;
}
function field(parent, text, id, value, type = "number") {
  const l = el(parent, "label", text);
  const n = el(l, "input");
  n.id = id;
  n.type = type;
  n.value = value;
  if (type === "number") n.step = "any";
  return n;
}
function selectField(parent, text, id, options) {
  const l = el(parent, "label", text);
  const s = el(l, "select");
  s.id = id;
  options.forEach((v) => {
    const o = el(s, "option", Array.isArray(v) ? v[1] : v);
    o.value = Array.isArray(v) ? v[0] : v;
  });
  return s;
}
function openView(id) {
  document.querySelectorAll(".view").forEach((v) => (v.hidden = v.id !== id));
  document.querySelectorAll("[data-tab]").forEach((b) => {
    if (b.dataset.tab === id) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  if (id === "workflow") guarded(loadHistory);
  if (id === "market") renderMarket();
  if (id === "accounting" && accountResult) renderAccounts();
  if (id === "valuation" && packet) forecastChart();
}
const accountingSection = section("accounting", "Financials");
const forecastSection = section("projections", "Forecast builder");
const marketSection = section("market", "Share price & performance");
const tabs = document.querySelector(".tabs");
[
  ["accounting", "Financials"],
  ["projections", "Forecasts"],
  ["market", "Share price"],
]
  .reverse()
  .forEach(([id, name]) => {
    const b = document.createElement("button");
    b.dataset.tab = id;
    b.textContent = name;
    tabs.prepend(b);
  });
const tabNames = {
  risk: "Risk",
  methods: "Calculators",
  knowledge: "Research",
  workflow: "Sources",
};
document.querySelectorAll(".tabs [data-tab]").forEach((b) => {
  b.textContent = tabNames[b.dataset.tab] || b.textContent;
  b.onclick = () => openView(b.dataset.tab);
});
const side = el(document.querySelector(".controls"), "nav", "", "side-nav");
side.setAttribute("aria-label", "Workspace");
el(side, "p", "Workspace", "side-label");
document.querySelectorAll(".tabs [data-tab]").forEach((b) => {
  const c = action(side, b.textContent, () => openView(b.dataset.tab));
  c.dataset.tab = b.dataset.tab;
});
document.querySelector(".controls").insertBefore(side, by("run"));
document.querySelector(".controls .guide").textContent =
  "Start with financials. Build a forecast, then compare what the shares could be worth.";
by("save").textContent = "Save analysis";
by("run").textContent = "Run valuation";
by("download").textContent = "Export run";
const currencyBar = el(accountingSection, "div", "", "workspace-tools");
selectField(
  currencyBar,
  "Reporting currency",
  "reporting-currency",
  currencyChoices,
);
selectField(
  currencyBar,
  "Display currency",
  "display-currency",
  currencyChoices,
);
field(currencyBar, "Exchange-rate date", "fx-date", "2026-11-04", "date");
action(currencyBar, "Convert display", convertDisplay);
el(
  accountingSection,
  "p",
  "All statement inputs are whole currency units. Display conversion uses one dated rate for comparison; it is not an accounting translation under IAS 21.",
  "currency-note",
);
el(accountingSection, "p", "", "currency-note").id = "fx-status";
const sourceTools = el(accountingSection, "div", "", "workspace-tools");
field(
  sourceTools,
  "Statement source",
  "account-source",
  "Fictional learning dataset",
  "text",
);
const actions = el(accountingSection, "div", "", "import-row");
action(actions, "Edit statements", () => {
  accountEditing = !accountEditing;
  renderAccounts();
});
action(actions, "Save statement edits", saveAccounts, "primary");
action(actions, "Use latest year in valuation", useLatest);
action(actions, "Download CSV", () =>
  download(
    new Blob([accountsCSV()], { type: "text/csv" }),
    "financial-statements.csv",
  ),
);
const uploadLabel = el(actions, "label", "Import statement CSV");
const file = el(uploadLabel, "input");
file.type = "file";
file.accept = ".csv";
file.id = "accounts-upload";
file.onchange = () => guarded(importAccounts);
el(
  accountingSection,
  "p",
  "Demo financials. Replace the figures or import your own CSV using the download as a template.",
  "subtle",
).id = "account-notice";
el(accountingSection, "p", "", "subtle").id = "account-status";
el(accountingSection, "div", "", "facts").id = "account-facts";
const chartPanel = el(accountingSection, "section", "", "panel");
el(chartPanel, "h3", "Revenue, earnings & cash flow");
el(chartPanel, "div").id = "account-chart";
const statementTabs = el(accountingSection, "div", "", "statement-tabs");
[
  ["income", "Income statement"],
  ["balance", "Balance sheet"],
  ["cash", "Cash flow"],
  ["ratios", "Ratios"],
].forEach(([key, text]) => {
  const b = action(statementTabs, text, () => {
    accountView = key;
    renderAccounts();
  });
  b.dataset.statement = key;
});
el(accountingSection, "div", "", "scroll account-grid").id = "account-table";
el(accountingSection, "p", "", "subtle").id = "account-conventions";
function demoAccounts() {
  return {
    currency: "ZAR",
    source: "Fictional learning dataset",
    periods: [2022, 2023, 2024, 2025].map((year, i) => {
      const revenue = [85, 96, 109, 120][i] * 1e6,
        cash = [5, 6, 7, 8][i] * 1e6,
        receivables = [10, 11, 13, 14][i] * 1e6,
        inventory = [8, 9, 10, 11][i] * 1e6,
        ppe = [32, 35, 39, 42][i] * 1e6,
        payables = [8, 9, 11, 12][i] * 1e6,
        debt = 23e6;
      return {
        year,
        revenue,
        cost_of_sales: revenue * 0.58,
        operating_expenses: revenue * 0.23,
        depreciation: revenue * 0.04,
        interest: 2.3e6,
        tax: (revenue * 0.15 - 2.3e6) * 0.27,
        cash,
        receivables,
        inventory,
        ppe,
        payables,
        debt,
        equity: cash + receivables + inventory + ppe - payables - debt,
        cfo: [9, 10.5, 12, 14][i] * 1e6,
        capex: revenue * 0.06,
        diluted_shares: 5e6,
      };
    }),
  };
}
async function analyzeAccounts() {
  accountResult = await (await api("/api/v1/accounting", accounts)).json();
  renderAccounts();
}
function money(v, d = 2) {
  return v == null ? "—" : fmt(v * fx.rate, d);
}
function displayValue(k, v, sourceCurrency = false) {
  if (v == null) return "—";
  if (ratios.has(k)) return pct(v);
  if (multiples.has(k)) return fmt(v) + "×";
  if (days.has(k)) return fmt(v, 1);
  if (k === "diluted_shares") return fmt(v, 0);
  return sourceCurrency
    ? fmt(v, k === "eps" ? 2 : 0)
    : money(v, k === "eps" ? 2 : 0);
}
const statementRows = {
  income: [
    "revenue",
    "cost_of_sales",
    "gross_profit",
    "operating_expenses",
    "ebitda",
    "depreciation",
    "ebit",
    "interest",
    "tax",
    "net_income",
    "eps",
  ],
  balance: [
    "cash",
    "receivables",
    "inventory",
    "ppe",
    "assets",
    "payables",
    "debt",
    "equity",
    "diluted_shares",
  ],
  cash: ["cfo", "capex", "fcf"],
  ratios: [
    "revenue_growth",
    "gross_margin",
    "ebitda_margin",
    "net_margin",
    "roe",
    "roa",
    "interest_coverage",
    "net_debt_ebitda",
    "cash_conversion",
    "accrual_ratio",
    "dso",
    "dio",
    "dpo",
    "cash_cycle",
  ],
};
function renderAccounts() {
  if (!accountResult) return;
  document
    .querySelectorAll("[data-statement]")
    .forEach((b) =>
      b.setAttribute(
        "aria-pressed",
        String(b.dataset.statement === accountView),
      ),
    );
  const rows = accountResult.rows;
  by("account-facts").replaceChildren();
  const last = rows.at(-1);
  [
    ["Revenue", money(last.revenue / 1e6) + "m"],
    ["Net profit", money(last.net_income / 1e6) + "m"],
    ["Free cash flow", money(last.fcf / 1e6) + "m"],
    ["Return on equity", pct(last.roe)],
  ].forEach(([label, value]) => {
    const n = el(by("account-facts"), "div");
    el(n, "span", label);
    el(n, "strong", value);
  });
  by("account-conventions").textContent = accountResult.conventions;
  by("account-table").replaceChildren();
  const t = el(by("account-table"), "table");
  const hr = el(el(t, "thead"), "tr");
  el(
    hr,
    "th",
    accountEditing
      ? `Edit in ${accounts.currency} · whole units`
      : `${fx.quote || accounts.currency} · whole units`,
  );
  rows.forEach((r) => el(hr, "th", String(r.year)));
  const body = el(t, "tbody");
  statementRows[accountView].forEach((k) => {
    const tr = el(body, "tr");
    el(tr, "th", labelOf(k));
    rows.forEach((r, i) => {
      const td = el(tr, "td");
      if (accountEditing && accountFields.includes(k)) {
        const n = el(td, "input");
        n.type = "number";
        n.step = "any";
        n.value = accounts.periods[i][k];
        n.setAttribute("aria-label", `${r.year} ${labelOf(k)}`);
        n.dataset.period = i;
        n.dataset.field = k;
        n.onchange = () => {
          accounts.periods[i][k] = Number(n.value);
          by("account-status").textContent =
            "Unsaved edits. Save to validate and update ratios.";
        };
      } else td.textContent = displayValue(k, r[k], accountEditing);
    });
  });
  drawBars(by("account-chart"), rows);
}
async function saveAccounts() {
  accounts.source = by("account-source").value;
  accountResult = await (
    await api("/api/v1/accounting?save=true", accounts)
  ).json();
  localStorage.setItem("valuation-accounts", JSON.stringify(accounts));
  accountEditing = false;
  renderAccounts();
  by("account-status").textContent =
    "Statements saved to the local database; balance sheets checked.";
}
async function useLatest() {
  await saveAccounts();
  const p = accounts.periods.at(-1);
  const currencyChanged = currentCase.currency !== accounts.currency;
  if (p.year >= Number(currentCase.valuation_date.slice(0, 4)))
    throw Error("Use a completed financial year before the valuation date.");
  invalidate();
  for (const k of [
    "revenue",
    "cash",
    "receivables",
    "inventory",
    "ppe",
    "payables",
    "debt",
    "equity",
    "diluted_shares",
  ])
    currentCase.opening[k] = p[k];
  currentCase.opening.excess_cash = Math.min(
    currentCase.opening.excess_cash,
    p.cash,
  );
  if (currencyChanged) {
    currentCase.opening.excess_cash = 0;
    currentCase.opening.non_operating_assets = 0;
    currentCase.opening.other_claims = 0;
    currentCase.peers = [];
  }
  currentCase.opening.source = accounts.source;
  currentCase.currency = accounts.currency;
  syncControls();
  await calculate();
  by("account-status").textContent =
    `${p.year} balances now drive the valuation in ${accounts.currency}.` +
    (currencyChanged
      ? " Previous-currency peers and bridge adjustments were cleared. Cash is treated as operating; review discount rates and tax assumptions for this company."
      : "");
}
async function convertDisplay() {
  const base = accounts.currency,
    quote = by("display-currency").value,
    requestedDate = by("fx-date").value;
  by("fx-status").textContent = "Fetching dated reference rate…";
  const result = await (
    await api(`/api/v1/fx?base=${base}&quote=${quote}&as_of=${requestedDate}`)
  ).json();
  if (
    accounts.currency !== base ||
    by("display-currency").value !== quote ||
    by("fx-date").value !== requestedDate
  ) {
    by("fx-status").textContent =
      "Currency selection changed while fetching. Convert display again to apply the new selection.";
    return;
  }
  fx = result;
  renderAccounts();
  renderProjections();
  renderMarket();
  by("fx-status").textContent =
    `1 ${base} = ${fmt(fx.rate, 6)} ${quote} · ${fx.date} · ${fx.source}. Financials and share-price displays only; valuation and calculators retain their labelled source currency.`;
}
by("reporting-currency").onchange = () => {
  by("account-status").textContent =
    "Statements are not linked to this currency yet. Use latest year in valuation after checking the denomination.";
  accounts.currency = by("reporting-currency").value;
  fx = { rate: 1, quote: accounts.currency };
  by("display-currency").value = accounts.currency;
  by("fx-status").textContent =
    "Reporting currency changed. Existing inputs keep their numerical amounts; confirm their original denomination before using them.";
  analyzeAccounts();
};
function accountsCSV() {
  return [
    "year," + accountFields.join(","),
    ...accounts.periods.map((p) =>
      [p.year, ...accountFields.map((k) => p[k])].join(","),
    ),
  ].join("\n");
}
async function importAccounts() {
  const f = file.files[0];
  if (!f) return;
  if (f.size > 1000000) throw Error("Use a CSV smaller than 1 MB.");
  const lines = (await f.text())
    .trim()
    .split(/\r?\n/)
    .map((l) => l.split(","));
  const header = lines.shift().map((s) => s.trim());
  if (header.join(",") !== "year," + accountFields.join(","))
    throw Error(
      "Use the columns in Download CSV, in the same order, with unformatted numbers.",
    );
  const candidate = {
    currency: by("reporting-currency").value,
    source: by("account-source").value,
    periods: lines.map((row) =>
      Object.fromEntries(header.map((k, i) => [k, Number(row[i])])),
    ),
  };
  const result = await (await api("/api/v1/accounting", candidate)).json();
  accounts = candidate;
  accountResult = result;
  accountEditing = false;
  fx = { rate: 1 };
  by("display-currency").value = accounts.currency;
  by("account-notice").textContent = "Imported financials · " + accounts.source;
  renderAccounts();
}
const NS = "http://www.w3.org/2000/svg";
function svgNode(parent, tag, attrs, text) {
  const n = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
  if (text) n.textContent = text;
  parent.append(n);
  return n;
}
function drawBars(parent, rows) {
  parent.replaceChildren();
  const width = Math.max(320, parent.clientWidth),
    height = 260;
  const svg = svgNode(parent, "svg", {
    viewBox: `0 0 ${width} ${height}`,
    class: "workspace-chart",
    role: "img",
    "aria-label":
      "Historical revenue, net income and operating cash flow; statement tables contain all values",
  });
  const values = rows.flatMap((r) => [r.revenue, r.net_income, r.cfo]);
  const lo = Math.min(0, ...values),
    hi = Math.max(1, ...values) * 1.1,
    range = hi - lo;
  const y = (v) => 220 - ((v - lo) / range) * 175;
  for (let i = 0; i < 4; i++) {
    const value = lo + (i * range) / 3;
    svgNode(svg, "line", { x1: 52, y1: y(value), x2: width - 8, y2: y(value) });
    svgNode(
      svg,
      "text",
      { x: 0, y: y(value) + 4, "font-size": 11 },
      money(value / 1e6, 0) + "m",
    );
  }
  const group = (width - 64) / rows.length,
    bw = Math.min(20, group / 4);
  rows.forEach((r, i) => {
    const x = 59 + i * group;
    ["revenue", "net_income", "cfo"].forEach((key, j) => {
      const rect = svgNode(svg, "rect", {
        x: x + j * (bw + 2),
        y: Math.min(y(r[key]), y(0)),
        width: bw,
        height: Math.max(1, Math.abs(y(r[key]) - y(0))),
        fill: ["#58a6ff", "#3fb950", "#d2a8ff"][j],
        rx: 2,
      });
      svgNode(rect, "title", {}, `${r.year} ${labelOf(key)}: ${money(r[key])}`);
    });
    svgNode(svg, "text", { x, y: 245, "font-size": 12 }, String(r.year));
  });
  [
    ["Revenue", "#58a6ff"],
    ["Net profit", "#3fb950"],
    ["Cash flow", "#d2a8ff"],
  ].forEach(([text, color], i) => {
    svgNode(svg, "rect", {
      x: 10 + (i * width) / 3,
      y: 10,
      width: 8,
      height: 8,
      fill: color,
    });
    svgNode(
      svg,
      "text",
      { x: 23 + (i * width) / 3, y: 19, "font-size": 12 },
      text,
    );
  });
}
// Editable annual operating schedules; global terminal settings remain explicit.
el(
  forecastSection,
  "p",
  "Set a different operating plan for each year. The engine links earnings, working capital, cash flow and the balance sheet.",
  "subtle",
);
const forecastTools = el(forecastSection, "div", "", "workspace-tools");
selectField(forecastTools, "View", "projection-view", [
  ["drivers", "Assumptions"],
  ["income", "Income statement"],
  ["balance", "Balance sheet"],
  ["cash", "Cash flow"],
]).onchange = renderProjections;
action(forecastTools, "Apply forecast", applyForecast, "primary");
action(forecastTools, "Reset annual assumptions", () => {
  currentCase.annual_drivers = [];
  syncControls();
  invalidate();
  renderProjections();
});
el(forecastSection, "div", "", "scroll account-grid").id = "projection-table";
const terminal = el(forecastSection, "div", "", "workspace-tools");
[
  ["wacc", "Discount rate", 14.5],
  ["terminal_growth", "Long-run growth", 4],
  ["terminal_roic", "Long-run return on capital", 14],
].forEach(([key, label, v]) =>
  field(terminal, label + " (%)", "terminal-" + key, v),
);
el(
  forecastSection,
  "p",
  "Annual operating assumptions are percentages of revenue, except growth, tax and borrowing rates. Debt stays fixed; dividends and new financing are not assumed. Long-run settings apply to terminal value.",
  "subtle",
);
const operatingKeys = [
  "revenue_growth",
  "ebitda_margin",
  "depreciation_rate",
  "capex_rate",
  "receivables_rate",
  "inventory_rate",
  "payables_rate",
  "tax_rate",
  "borrowing_rate",
];
function renderProjections() {
  if (!currentCase || !packet) return;
  const mode = by("projection-view").value;
  by("projection-table").replaceChildren();
  const t = el(by("projection-table"), "table"),
    head = el(el(t, "thead"), "tr");
  el(
    head,
    "th",
    mode === "drivers"
      ? "Annual assumptions (%)"
      : `${currentCase.currency} · whole units`,
  );
  for (let i = 0; i < currentCase.years; i++)
    el(
      head,
      "th",
      String(Number(currentCase.valuation_date.slice(0, 4)) + i + 1) + "E",
    );
  const body = el(t, "tbody");
  const keys =
    mode === "drivers"
      ? operatingKeys
      : mode === "income"
        ? [
            "revenue",
            "ebitda",
            "depreciation",
            "ebit",
            "interest",
            "tax",
            "net_income",
          ]
        : mode === "balance"
          ? [
              "cash",
              "receivables",
              "inventory",
              "ppe",
              "assets",
              "payables",
              "debt",
              "equity",
            ]
          : ["cfo", "cfi", "cff", "change_cash", "fcff"];
  keys.forEach((k) => {
    const row = el(body, "tr");
    el(row, "th", labelOf(k));
    for (let i = 0; i < currentCase.years; i++) {
      const td = el(row, "td");
      if (mode === "drivers") {
        const n = el(td, "input");
        n.type = "number";
        n.step = "0.1";
        n.value = Number(
          (
            (currentCase.annual_drivers?.[i] || currentCase.drivers)[k] * 100
          ).toFixed(5),
        );
        n.dataset.year = i;
        n.dataset.driver = k;
        n.setAttribute("aria-label", `Year ${i + 1} ${labelOf(k)} percent`);
        n.oninput = () => {
          if (!currentCase.annual_drivers?.length)
            currentCase.annual_drivers = Array.from(
              { length: currentCase.years },
              () => structuredClone(currentCase.drivers),
            );
          currentCase.annual_drivers[i][k] = Number(n.value) / 100;
          syncControls();
          invalidate();
          status(
            "Forecast edits pending. Apply forecast to update all calculations.",
          );
        };
      } else td.textContent = fmt(packet.result.statements[i][k], 0);
    }
  });
}
async function applyForecast() {
  if (by("projection-view").value === "drivers") {
    currentCase.annual_drivers = Array.from(
      { length: currentCase.years },
      (_, i) =>
        structuredClone(currentCase.annual_drivers?.[i] || currentCase.drivers),
    );
    document
      .querySelectorAll("[data-driver][data-year]")
      .forEach(
        (n) =>
          (currentCase.annual_drivers[Number(n.dataset.year)][
            n.dataset.driver
          ] = Number(n.value) / 100),
      );
  }
  for (const k of ["wacc", "terminal_growth", "terminal_roic"])
    currentCase.drivers[k] = Number(by("terminal-" + k).value) / 100;
  syncControls();
  invalidate();
  await calculate();
}
// Structured calculator fields replace implementation syntax.
const methodForm = el(
  by("method-input").parentElement,
  "div",
  "",
  "method-fields",
);
methodForm.id = "method-fields";
by("method-input").classList.add("method-hidden");
const inputLabel = document.querySelector('label[for="method-input"]');
if (inputLabel) inputLabel.classList.add("method-hidden");
const results = el(
  by("method-output").parentElement,
  "div",
  "",
  "method-results",
);
results.id = "method-results";
const percentFields = new Set([
  "risk_free",
  "equity_risk_premium",
  "debt_weight",
  "tax_rate",
  "pretax_cost_debt",
  "country_premium",
  "discount_rate",
  "terminal_growth",
  "tax_shield_rate",
  "survival",
  "spot_rates",
  "lower",
  "upper",
]);
const percentResults = new Set([
  "cost_equity",
  "after_tax_cost_debt",
  "wacc",
  "accrual_ratio",
  "cash_return_on_assets",
  "directional_accuracy",
  "skill_vs_naive",
]);
function buildMethodFields() {
  chooseMethod();
  const sample = JSON.parse(by("method-input").value);
  methodForm.replaceChildren();
  results.textContent = "Enter your assumptions, then calculate.";
  function build(obj, parent, path = []) {
    Object.entries(obj).forEach(([k, v]) => {
      if (k === "case" || k === "method") return;
      if (Array.isArray(v)) {
        const fs = el(parent, "fieldset");
        el(fs, "legend", labelOf(k) + (percentFields.has(k) ? " (%)" : ""));
        if (v.length && typeof v[0] === "object") {
          el(
            fs,
            "p",
            "Uses the example price series. Import your own price history in Share price.",
            "subtle",
          );
          return;
        }
        const holder = el(fs, "div", "", "array-fields");
        v.forEach((val, i) => {
          const n = field(
            holder,
            `Year ${i + 1}`,
            "mf-" + [...path, k, i].join("-"),
            percentFields.has(k) ? val * 100 : val,
          );
          n.dataset.scale = percentFields.has(k) ? "100" : "1";
          n.dataset.path = JSON.stringify([...path, k, i]);
        });
        return;
      }
      if (typeof v === "object" && v !== null) return;
      const n = field(
        parent,
        labelOf(k) + (percentFields.has(k) ? " (%)" : ""),
        "mf-" + [...path, k].join("-"),
        percentFields.has(k) ? v * 100 : v,
        typeof v === "number" ? "number" : "text",
      );
      n.dataset.path = JSON.stringify([...path, k]);
      n.dataset.scale = percentFields.has(k) ? "100" : "1";
    });
  }
  build(sample, methodForm);
  el(
    methodForm,
    "p",
    `Monetary inputs and results use ${currentCase?.currency || "source currency"}, whole units. Rates are percentages; beta and multiples are ratios.`,
    "subtle",
  );
  methodForm.oninput = () => {
    results.textContent =
      "Inputs changed. Calculate again to update the result.";
  };
}
by("method-choice").onchange = buildMethodFields;
function presentResult(value, parent) {
  if (Array.isArray(value)) {
    const ul = el(parent, "ul");
    value.slice(0, 30).forEach((v) => {
      const li = el(ul, "li");
      if (typeof v === "object") presentResult(v, li);
      else li.textContent = typeof v === "number" ? fmt(v, 4) : String(v);
    });
    return;
  }
  if (value && typeof value === "object") {
    const dl = el(parent, "dl");
    Object.entries(value).forEach(([k, v]) => {
      if (k === "case" || k === "bars") return;
      el(dl, "dt", labelOf(k));
      const dd = el(dl, "dd");
      if (typeof v === "object" && v !== null) presentResult(v, dd);
      else
        dd.textContent =
          typeof v === "number"
            ? percentResults.has(k)
              ? pct(v)
              : fmt(v, 4)
            : String(v ?? "Unavailable");
    });
  }
}
by("calculate-method").onclick = () =>
  guarded(async () => {
    const sample = JSON.parse(by("method-input").value);
    methodForm.querySelectorAll("[data-path]").forEach((n) => {
      const path = JSON.parse(n.dataset.path);
      let target = sample;
      path.slice(0, -1).forEach((k) => (target = target[k]));
      target[path.at(-1)] =
        n.type === "number"
          ? Number(n.value) / Number(n.dataset.scale || 1)
          : n.value;
    });
    if (sample.case) sample.case = currentCase;
    if (sample.bars && marketImported) {
      sample.bars = marketBars;
      sample.source = marketSource;
    }
    const name = by("method-choice").value,
      research = [
        "reverse-dcf",
        "earnings-quality",
        "forecast-evaluation",
      ].includes(name),
      route = research
        ? name
        : ["capital-cost", "liability"].includes(name)
          ? name
          : "cashflows";
    results.textContent = "Calculating…";
    const output = await (
      await api(
        (research ? "/api/v1/research/" : "/api/v1/methods/") + route,
        sample,
      )
    ).json();
    results.replaceChildren();
    presentResult(output, results);
  }, results);
// Market history is a labelled demo until the user imports their own OHLCV file.
let marketImported = false,
  marketSource = "Synthetic price history · not a listed security",
  marketBars = Array.from({ length: 60 }, (_, i) => {
    const open = 22 + i * 0.08 + Math.sin(i * 0.7) * 0.8,
      close = open + Math.cos(i * 1.3) * 0.7;
    return {
      date: new Date(Date.UTC(2026, 6, i + 1)).toISOString().slice(0, 10),
      open,
      high: Math.max(open, close) + 0.4,
      low: Math.min(open, close) - 0.4,
      close,
      volume: 10000 + Math.round((Math.sin(i) + 1) * 7000),
    };
  });
const marketTools = el(marketSection, "div", "", "workspace-tools");
selectField(marketTools, "Quote currency", "quote-currency", [
  ...currencyChoices,
  "ZAC",
  "GBX",
]).onchange = renderMarket;
field(marketTools, "Price source", "market-source", marketSource, "text");
selectField(marketTools, "Price history", "market-window", [
  ["20", "Last 20 observations"],
  ["60", "Last 60 observations"],
  ["250", "Last 250 observations"],
]).onchange = renderMarket;
const priceLabel = el(marketTools, "label", "Import OHLCV CSV");
const priceFile = el(priceLabel, "input");
priceFile.type = "file";
priceFile.accept = ".csv";
priceFile.id = "price-upload";
priceFile.onchange = () =>
  guarded(async () => {
    const f = priceFile.files[0];
    if (!f) return;
    if (f.size > 2000000) throw Error("Use a price CSV smaller than 2 MB.");
    const lines = (await f.text())
      .trim()
      .split(/\r?\n/)
      .map((s) => s.split(","));
    if (lines.shift().join(",") !== "date,open,high,low,close,volume")
      throw Error(
        "CSV columns: date,open,high,low,close,volume. Prices must use the selected quote currency.",
      );
    const bars = lines.map((r) => ({
      date: r[0],
      open: +r[1],
      high: +r[2],
      low: +r[3],
      close: +r[4],
      volume: +r[5],
    }));
    if (
      bars.length < 2 ||
      bars.length > 5000 ||
      bars.some(
        (b, i) =>
          !/^\d{4}-\d{2}-\d{2}$/.test(b.date) ||
          !Number.isFinite(Date.parse(b.date)) ||
          b.date > currentCase.valuation_date ||
          (i && b.date <= bars[i - 1].date) ||
          ![b.open, b.high, b.low, b.close, b.volume].every(Number.isFinite) ||
          b.low <= 0 ||
          b.volume < 0 ||
          b.high < Math.max(b.open, b.close) ||
          b.low > Math.min(b.open, b.close),
      )
    )
      throw Error(
        "Use 2–5,000 ordered, unique, valid daily bars dated on or before the valuation date.",
      );
    marketBars = bars;
    marketImported = true;
    marketSource = by("market-source").value;
    renderMarket();
  });
action(marketTools, "Download price template", () =>
  download(
    new Blob(
      [
        "date,open,high,low,close,volume\n" +
          marketBars
            .map((b) =>
              [b.date, b.open, b.high, b.low, b.close, b.volume].join(","),
            )
            .join("\n"),
      ],
      { type: "text/csv" },
    ),
    "price-history.csv",
  ),
);
el(marketSection, "p", "", "subtle").id = "market-note";
el(marketSection, "div", "", "facts").id = "market-facts";
el(marketSection, "div").id = "market-chart";
el(
  marketSection,
  "p",
  "Green candles closed above their open; red candles closed below. Returns exclude dividends. Imported prices should use a consistent split-adjustment basis.",
  "subtle",
);
const valuationPanel = el(marketSection, "section", "", "panel");
el(valuationPanel, "h3", "What could a share be worth?");
const vm = el(valuationPanel, "div", "", "workspace-tools");
field(vm, "Target P/E (×)", "target-pe", 15);
field(vm, "Target price / book (×)", "target-pb", 2);
field(vm, "Next dividend per share (source currency)", "next-dividend", 1);
field(vm, "Cost of equity (%)", "market-ke", 14);
field(vm, "Dividend growth (%)", "dividend-growth", 4);
action(vm, "Compare models", renderMarket, "primary");
el(valuationPanel, "div", "", "scroll").id = "share-models";
el(
  valuationPanel,
  "p",
  "P/E uses latest historical EPS; price/book uses latest book equity. Dividend value assumes perpetual sustainable growth. These methods use different economic assumptions and are not averaged.",
  "subtle",
);
const priceDetails = el(marketSection, "details");
el(priceDetails, "summary", "Price history table");
el(priceDetails, "div", "", "scroll").id = "price-table";
function renderMarket() {
  if (!accountResult || !packet) return;
  const quote = by("quote-currency").value,
    source = quote === "ZAC" ? "ZAR" : quote === "GBX" ? "GBP" : quote,
    unit = ["ZAC", "GBX"].includes(quote) ? 0.01 : 1;
  const compatible = source === accounts.currency;
  const factor = compatible ? unit * fx.rate : unit;
  const display = compatible ? fx.quote || accounts.currency : source;
  const bars = marketBars.slice(-Number(by("market-window").value));
  const latest = bars.at(-1),
    first = bars[0];
  by("market-note").textContent =
    marketSource +
    ` · ${display} · ${first.date} to ${latest.date}` +
    (compatible
      ? ""
      : " · Currency differs from financials. Valuation comparison is disabled.");
  by("market-facts").replaceChildren();
  [
    ["Last close", fmt(latest.close * factor)],
    ["Period price return", pct(latest.close / first.close - 1)],
    ["Period high", fmt(Math.max(...bars.map((b) => b.high)) * factor)],
    ["Period low", fmt(Math.min(...bars.map((b) => b.low)) * factor)],
  ].forEach(([label, value]) => {
    const d = el(by("market-facts"), "div");
    el(d, "span", label);
    el(d, "strong", value);
  });
  by("market-chart").replaceChildren();
  const s = svgNode(by("market-chart"), "svg", {
    viewBox: `0 0 ${Math.max(320, by("market-chart").clientWidth)} 300`,
    class: "workspace-chart",
    role: "img",
    "aria-label":
      "Candlestick price chart; values available in Price history table",
  });
  const chartWidth = Math.max(320, by("market-chart").clientWidth);
  const lo = Math.min(...bars.map((b) => b.low)),
    hi = Math.max(...bars.map((b) => b.high)),
    range = hi - lo || 1;
  const y = (v) => 245 - ((v - lo) / range) * 210;
  for (let i = 0; i < 5; i++) {
    const value = lo + (i * range) / 4;
    svgNode(s, "line", {
      x1: 65,
      y1: y(value),
      x2: chartWidth - 15,
      y2: y(value),
    });
    svgNode(
      s,
      "text",
      { x: 3, y: y(value) + 4, "font-size": 12 },
      fmt(value * factor),
    );
  }
  bars.forEach((b, i) => {
    const x = 65 + (i * (chartWidth - 80)) / bars.length,
      w = Math.max(1, ((chartWidth - 80) / bars.length) * 0.6),
      up = b.close >= b.open,
      color = up ? "#3fb950" : "#f85149";
    svgNode(s, "line", {
      x1: x,
      y1: y(b.high),
      x2: x,
      y2: y(b.low),
      class: up ? "candle-up" : "candle-down",
    });
    const rect = svgNode(s, "rect", {
      x: x - w / 2,
      y: Math.min(y(b.open), y(b.close)),
      width: w,
      height: Math.max(1, Math.abs(y(b.close) - y(b.open))),
      fill: color,
    });
    svgNode(
      rect,
      "title",
      {},
      `${b.date} O ${fmt(b.open * factor)} H ${fmt(b.high * factor)} L ${fmt(b.low * factor)} C ${fmt(b.close * factor)}`,
    );
  });
  svgNode(s, "text", { x: 65, y: 280, "font-size": 12 }, first.date);
  svgNode(
    s,
    "text",
    { x: chartWidth - 100, y: 280, "font-size": 12 },
    latest.date,
  );
  table(
    by("price-table"),
    ["Date", `Open (${display})`, "High", "Low", "Close", "Volume"],
    bars.map((b) => [
      b.date,
      ...["open", "high", "low", "close"].map((k) => fmt(b[k] * factor)),
      fmt(b.volume, 0),
    ]),
  );
  const p = accountResult.rows.at(-1),
    ke = +by("market-ke").value / 100,
    g = +by("dividend-growth").value / 100,
    pe = +by("target-pe").value,
    pb = +by("target-pb").value,
    div = +by("next-dividend").value;
  const caseMatches =
    accounts.currency === currentCase.currency &&
    ["revenue", "cash", "debt", "equity", "diluted_shares"].every(
      (k) => accounts.periods.at(-1)[k] === currentCase.opening[k],
    );
  const models = [
    ["Discounted cash flow", caseMatches ? packet.result.base.per_share : null],
    ["Peer EV / EBITDA", caseMatches ? packet.result.comps.per_share : null],
    ["Price / earnings", pe > 0 && p.eps > 0 ? p.eps * pe : null],
    [
      "Price / book",
      pb > 0 && p.equity > 0 ? (p.equity / p.diluted_shares) * pb : null,
    ],
    [
      "Dividend growth",
      ke > g && ke > 0 && g >= -0.5 && div >= 0 ? div / (ke - g) : null,
    ],
  ];
  table(
    by("share-models"),
    [
      "Model",
      `Value / share (${fx.quote || accounts.currency})`,
      "Difference from close",
    ],
    models.map(([name, v]) => [
      name,
      v == null ? "Not supported" : money(v),
      v != null && compatible
        ? pct(v / (latest.close * unit) - 1)
        : "Not comparable",
    ]),
  );
}
const originalShow = show;
show = function (p) {
  originalShow(p);
  renderProjections();
  renderMarket();
  for (const k of ["wacc", "terminal_growth", "terminal_roic"])
    by("terminal-" + k).value = currentCase.drivers[k] * 100;
};
const originalWorkflow = renderWorkflow;
renderWorkflow = function (w) {
  originalWorkflow(w);
  if (w.synthetic) {
    const state = by("workflow-gates").querySelectorAll(".state")[1];
    if (state) state.textContent = "Demo data";
  }
  by("workflow-gates")
    .querySelectorAll("strong")
    .forEach((n) => (n.textContent = n.textContent.replace(/^\d+ \/ /, "")));
};
async function startWorkspace() {
  try {
    accounts =
      JSON.parse(localStorage.getItem("valuation-accounts")) || demoAccounts();
  } catch {
    accounts = demoAccounts();
  }
  by("reporting-currency").value = accounts.currency;
  by("display-currency").value = accounts.currency;
  by("quote-currency").value = accounts.currency;
  by("account-source").value = accounts.source;
  await analyzeAccounts();
  buildMethodFields();
  renderProjections();
  renderMarket();
  openView("accounting");
}
guarded(startWorkspace);

// Keep feedback visible on mobile and place the footer after every workspace view.
by("workspace").append(document.querySelector("footer"));
by("workspace").insertBefore(by("status"), by("stale"));
document.querySelector(".controls p.guide").textContent =
  "Start with financials. Build a forecast, then compare share values.";
by("methods").querySelector("h2").textContent = "Financial calculators";
by("methods").querySelector("h2 + p").textContent =
  "Choose a model and enter your assumptions. Results stay separate from the company forecast.";
by("methods").querySelector("h3").textContent = "Results";
methodForm.parentElement.append(by("calculate-method"));
by("method-chart").hidden = true;
const sourceHeading = by("knowledge").querySelector("h2");
if (sourceHeading) sourceHeading.textContent = "Find a company";
window.addEventListener("resize", () => {
  if (accountResult) drawBars(by("account-chart"), accountResult.rows);
  if (!marketSection.hidden) renderMarket();
});

for (const key of ["wacc", "terminal_growth", "terminal_roic"])
  by("terminal-" + key).addEventListener("input", () => {
    invalidate();
    status(
      "Discount assumptions changed. Apply forecast to update valuations.",
    );
  });
