"use strict";
const by = (id) => document.getElementById(id);
const fmt = (v, d = 2) =>
  v == null || !Number.isFinite(v)
    ? "Unavailable"
    : new Intl.NumberFormat(undefined, {
        maximumFractionDigits: d,
        minimumFractionDigits: d,
      }).format(v);
const pct = (v) => (v == null ? "Unavailable" : fmt(v * 100, 1) + "%");
const title = (s) => s.replaceAll("_", " ").replaceAll("-", " ");
const el = (parent, tag, text = "", className = "") => {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  parent.append(node);
  return node;
};
const exports = [...document.querySelectorAll("[data-kind]")];
let currentCase,
  packet,
  completedCase,
  runId = null,
  revision = 0,
  requestNumber = 0,
  timer,
  searchTimer,
  searchNumber = 0,
  simulationDirty = false;
const controls = [
  ["revenue_growth", "Revenue growth", -20, 40, "Volume and pricing together"],
  ["ebitda_margin", "EBITDA margin", 0, 50, "Operating earnings / revenue"],
  ["capex_rate", "Capital expenditure", 0, 30, "Reinvestment / revenue"],
  [
    "wacc",
    "Cost of capital",
    2,
    35,
    "Return required by all capital providers",
  ],
  [
    "terminal_growth",
    "Terminal growth",
    -5,
    12,
    "Sustainable growth beyond the forecast",
  ],
  [
    "terminal_roic",
    "Terminal ROIC",
    1,
    50,
    "Return on future invested capital",
  ],
];
function status(message, error = false) {
  by("status").textContent = message;
  by("status").classList.toggle("error", error);
}
async function guarded(work, target) {
  try {
    return await work();
  } catch (error) {
    status(error.message, true);
    if (target) target.textContent = error.message;
  }
}
async function api(path, payload) {
  const response = await fetch(
    path,
    payload === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
  );
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = response.statusText;
    }
    throw Error(
      typeof detail === "string" ? detail : JSON.stringify(detail, null, 2),
    );
  }
  return response;
}
function invalidate() {
  revision++;
  requestNumber++;
  clearTimeout(timer);
  by("stale").hidden = !packet;
  by("download").disabled = true;
  exports.forEach((b) => (b.disabled = true));
  runId = null;
  by("add-evidence").disabled = true;
  by("active-run").textContent = "Save the current case to attach evidence.";
  by("evidence-list").replaceChildren();
  by("risk-output").replaceChildren();
  el(
    by("risk-output"),
    "p",
    "Inputs changed. Run the simulation for this case.",
    "empty",
  );
  by("macro-result").textContent = "";
}
function syncJSON() {
  by("input").value = JSON.stringify(currentCase, null, 2);
}
function syncControls() {
  by("company-input").value = currentCase.company;
  controls.forEach(([key, , min, max]) => {
    const value = currentCase.drivers[key] * 100;
    by(key).value = Number(value.toFixed(6));
    by(key + "-range").min = Math.min(min, value);
    by(key + "-range").max = Math.max(max, value);
    by(key + "-range").value = value;
  });
  by("data-label").textContent =
    currentCase.currency +
    " · " +
    currentCase.valuation_date +
    " · " +
    (/fictional|synthetic/i.test(
      currentCase.opening.source + currentCase.drivers.source,
    )
      ? "Fictional demonstration"
      : "Analyst-supplied case");
  syncJSON();
}
for (const [key, label, min, max, hint] of controls) {
  const root = el(by("driver-controls"), "div", "", "driver");
  const top = el(root, "div", "", "driver-top");
  const lab = el(top, "label", label);
  lab.htmlFor = key;
  const input = el(top, "input");
  Object.assign(input, { id: key, type: "number", step: "0.1" });
  input.setAttribute("aria-label", label + " percent");
  const slider = el(root, "input");
  Object.assign(slider, {
    id: key + "-range",
    type: "range",
    min,
    max,
    step: "0.1",
  });
  slider.setAttribute("aria-label", label + " slider");
  el(root, "small", hint, "guide");
  for (const node of [input, slider])
    node.addEventListener("input", () => {
      if (!currentCase) return;
      invalidate();
      if (node.value === "" || !Number.isFinite(Number(node.value))) {
        status("Enter a numeric assumption before calculating.", true);
        return;
      }
      currentCase.drivers[key] = Number(node.value) / 100;
      input.value = node.value;
      slider.value = node.value;
      syncJSON();
      timer = setTimeout(() => guarded(() => calculate()), 350);
    });
}
by("company-input").oninput = () => {
  if (!currentCase) return;
  invalidate();
  currentCase.company = by("company-input").value;
  syncJSON();
};
by("input").oninput = () => {
  invalidate();
  status("JSON edits pending. Apply JSON to validate and calculate.");
};
function table(host, headers, rows) {
  host.replaceChildren();
  const t = el(host, "table");
  const tr = el(el(t, "thead"), "tr");
  headers.forEach((x) => {
    const th = el(tr, "th", x);
    th.scope = "col";
  });
  const body = el(t, "tbody");
  rows.forEach((row) => {
    const r = el(body, "tr");
    row.forEach((v, i) => {
      const cell = el(r, i === 0 ? "th" : "td", String(v));
      if (i === 0) cell.scope = "row";
    });
  });
  return t;
}
function metrics(host, items) {
  host.replaceChildren();
  items.forEach(([label, v, note]) => {
    const item = el(host, "div", "", "value-item");
    el(item, "p", label);
    el(item, "strong", v);
    el(item, "small", note);
  });
}
const ns = "http://www.w3.org/2000/svg";
function svgNode(parent, tag, attrs = {}, text) {
  const node = document.createElementNS(ns, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  parent.append(node);
  return node;
}
function lineChart(
  host,
  series,
  labels,
  description,
  { band = null, scale = 1e6 } = {},
) {
  host.replaceChildren();
  const width = Math.max(320, host.clientWidth || 820),
    right = width - 25;
  const svg = svgNode(host, "svg", {
    viewBox: `0 0 ${width} 250`,
    role: "img",
    "aria-label": description,
  });
  svgNode(svg, "title", {}, description);
  const values = series
    .flatMap((s) => s.values)
    .concat(band ? band.low.concat(band.high) : []);
  let low = Math.min(0, ...values),
    high = Math.max(0, ...values);
  if (high === low) high = low + 1;
  const span = high - low;
  high += span * 0.1;
  low -= span * 0.05;
  const x = (i) => 58 + (i * (right - 58)) / Math.max(1, labels.length - 1);
  const y = (v) => 210 - ((v - low) / (high - low)) * 184;
  for (let i = 0; i < 5; i++) {
    const v = low + ((high - low) * i) / 4;
    svgNode(svg, "line", {
      x1: 58,
      x2: right,
      y1: y(v),
      y2: y(v),
      class: "axis",
    });
    svgNode(
      svg,
      "text",
      { x: 48, y: y(v) + 4, "text-anchor": "end" },
      fmt(v / scale, 1),
    );
  }
  labels.forEach((s, i) =>
    svgNode(svg, "text", { x: x(i), y: 238, "text-anchor": "middle" }, s),
  );
  if (band) {
    const points = band.high
      .map((v, i) => `${x(i)},${y(v)}`)
      .concat(band.low.map((v, i) => `${x(i)},${y(v)}`).reverse())
      .join(" ");
    svgNode(svg, "polygon", { points, fill: "#d5e4d7" });
  }
  series.forEach((s) => {
    svgNode(svg, "polyline", {
      points: s.values.map((v, i) => `${x(i)},${y(v)}`).join(" "),
      fill: "none",
      stroke: s.color,
      "stroke-width": 2.5,
      "stroke-dasharray": s.dashed ? "6 4" : "none",
    });
    s.values.forEach((v, i) => {
      const c = svgNode(svg, "circle", {
        cx: x(i),
        cy: y(v),
        r: 4,
        fill: s.color,
        tabindex: 0,
        "aria-label": `${s.name}, ${labels[i]}, ${fmt(v)}`,
      });
      svgNode(c, "title", {}, `${s.name} · ${labels[i]}: ${fmt(v)}`);
    });
  });
}
function forecastChart() {
  if (!packet) return;
  const key = by("chart-metric").value;
  const r = packet.result;
  lineChart(
    by("forecast-chart"),
    [
      {
        name: "Base",
        values: r.statements.map((x) => x[key]),
        color: "#176854",
      },
      {
        name: "Scenario",
        values: r.scenario_statements.map((x) => x[key]),
        color: "#a64d29",
        dashed: true,
      },
    ],
    r.statements.map((x) => "Y" + x.year),
    `${title(key)} in ${r.inputs.currency}; chart values in millions. Exact values in the forecast table.`,
  );
}
function renderWorkflow(workflow) {
  by("workflow-gates").replaceChildren();
  workflow.gates.forEach((g) => {
    const row = el(by("workflow-gates"), "div", "", "gate");
    el(row, "strong", g.stage);
    el(row, "span", g.status, "state " + g.status);
    el(row, "p", g.detail);
  });
}
function show(p) {
  packet = p;
  const r = p.result,
    a = p.analysis,
    d = r.inputs;
  completedCase = structuredClone(d);
  by("company").textContent = d.company;
  by("meta").textContent =
    `${d.currency} · ${d.valuation_date} · ${d.years}-year forecast · Model ${r.version} · ${r.input_sha256.slice(0, 10)}`;
  document
    .querySelectorAll(".currency")
    .forEach((n) => (n.textContent = d.currency));
  metrics(by("metrics"), [
    [
      "Base DCF / share",
      fmt(r.base.per_share),
      "Discounted operating cash flows",
    ],
    [
      "Risk scenario / share",
      fmt(r.scenario.per_share),
      "Supplied ESG / operating shocks",
    ],
    [
      "Peer indication / share",
      fmt(r.comps.per_share),
      `${r.comps.eligible} eligible peers · forward EV/EBITDA`,
    ],
  ]);
  forecastChart();
  table(
    by("forecast"),
    ["Metric", ...r.statements.map((x) => "Year " + x.year)],
    [
      "revenue",
      "ebitda",
      "ebit",
      "net_income",
      "cfo",
      "cfi",
      "cash",
      "debt",
      "fcff",
    ].map((k) => [title(k), ...r.statements.map((row) => fmt(row[k]))]),
  );
  const rates = [...new Set(r.sensitivity.map((x) => x.wacc))],
    growths = [...new Set(r.sensitivity.map((x) => x.growth))];
  const grid = table(
    by("sensitivity"),
    ["WACC / g", ...growths.map(pct)],
    rates.map((w) => [pct(w), ...growths.map(() => "")]),
  );
  const valid = r.sensitivity
    .filter((x) => x.per_share != null)
    .map((x) => x.per_share);
  const min = Math.min(...valid),
    max = Math.max(...valid);
  [...grid.tBodies[0].rows].forEach((row, i) =>
    growths.forEach((g, j) => {
      const v = r.sensitivity.find(
        (x) => x.wacc === rates[i] && x.growth === g,
      );
      const cell = row.cells[j + 1];
      if (v.per_share == null) {
        cell.textContent = "Unavailable";
        return;
      }
      const b = el(cell, "button", fmt(v.per_share));
      b.setAttribute(
        "aria-label",
        `Apply WACC ${pct(v.wacc)} and growth ${pct(v.growth)}; value ${fmt(v.per_share)} per share`,
      );
      const ratio = (v.per_share - min) / (max - min || 1);
      cell.style.background = `hsl(137 22% ${94 - ratio * 24}%)`;
      b.onclick = () => {
        invalidate();
        currentCase.drivers.wacc = v.wacc;
        currentCase.drivers.terminal_growth = v.growth;
        syncControls();
        guarded(() => calculate());
      };
    }),
  );
  by("bridge").replaceChildren();
  const o = d.opening;
  const bridge = [
    ["Explicit forecast PV", r.base.explicit_pv],
    ["Terminal value PV", r.base.terminal_pv],
    ["Excess cash", o.excess_cash],
    ["Other assets", o.non_operating_assets],
    ["Debt", -o.debt],
    ["Other claims", -o.other_claims],
    ["Equity value", r.base.equity_value],
  ];
  const limit = Math.max(1, ...bridge.map((x) => Math.abs(x[1] || 0)));
  bridge.forEach(([label, v], i) => {
    const row = el(
      by("bridge"),
      "div",
      "",
      "bridge-row" +
        (v < 0 ? " negative" : "") +
        (i === bridge.length - 1 ? " total" : ""),
    );
    el(row, "span", label);
    el(row, "span", v == null ? "Unavailable" : fmt(v / 1e6));
    if (v != null) {
      const bar = el(row, "div", "", "bridge-bar");
      bar.style.width = (Math.abs(v) / limit) * 100 + "%";
    }
  });
  by("terminal-note").textContent =
    `Terminal share of EV: ${pct(a.terminal_value_share)} · terminal reinvestment: ${pct(a.terminal_reinvestment_rate)}. ${r.base.reason || ""}`;
  by("tornado").replaceChildren();
  const all = a.tornado
    .flatMap((x) => [x.low_input_value, x.high_input_value])
    .filter((x) => x != null);
  if (a.base_per_share != null) all.push(a.base_per_share);
  const lo = Math.min(...all),
    hi = Math.max(...all),
    pos = (v) => ((v - lo) / (hi - lo || 1)) * 100;
  for (const t of [...a.tornado].sort(
    (x, y) =>
      Math.abs((y.high_input_value ?? 0) - (y.low_input_value ?? 0)) -
      Math.abs((x.high_input_value ?? 0) - (x.low_input_value ?? 0)),
  )) {
    const row = el(by("tornado"), "div", "", "tornado-row");
    const name = el(row, "span", title(t.driver));
    el(name, "small", ` · ±${t.shock_pp} pp`);
    const track = el(row, "div", "", "tornado-track");
    if (t.low_input_value != null && t.high_input_value != null) {
      const bar = el(track, "div", "", "tornado-range");
      bar.style.left =
        pos(Math.min(t.low_input_value, t.high_input_value)) + "%";
      bar.style.width =
        Math.abs(pos(t.high_input_value) - pos(t.low_input_value)) + "%";
    }
    if (a.base_per_share != null) {
      const center = el(track, "div", "", "tornado-center");
      center.style.left = pos(a.base_per_share) + "%";
    }
    el(row, "span", `${fmt(t.low_input_value)} / ${fmt(t.high_input_value)}`);
  }
  el(
    by("tornado"),
    "p",
    "Numbers show lower-input / higher-input valuations. The dark marker is the base case.",
    "small",
  );
  table(
    by("ratios"),
    ["Year", "ROIC", "Economic profit", "Interest cover", "FCFF margin"],
    a.ratios.map((x) => [
      x.year,
      pct(x.roic),
      fmt(x.economic_profit),
      fmt(x.interest_coverage),
      pct(x.fcff_margin),
    ]),
  );
  table(
    by("peers"),
    ["Peer", "Forward EV/EBITDA", "Included"],
    a.peers.map((x) => [x.name, fmt(x.multiple), x.eligible ? "Yes" : "No"]),
  );
  by("checks").replaceChildren();
  for (const text of [
    ...r.checks,
    ...d.risks.map(
      (x) =>
        `${x.issue}: ${x.change_pp} pp ${title(x.driver)}, years ${x.start}–${x.end}. ${x.source}`,
    ),
  ])
    el(by("checks"), "li", text);
  renderWorkflow(p.workflow);
  by("stale").hidden = true;
  by("download").disabled = false;
  exports.forEach((b) => (b.disabled = false));
  runId = p.run_id;
  by("add-evidence").disabled = !runId;
  by("active-run").textContent = runId
    ? "Evidence attaches to run " + runId
    : "Save this research run to attach evidence.";
  by("evidence-list").replaceChildren();
  if (p.simulation) {
    simulationDirty = false;
    syncRiskSettings(p.simulation.settings);
    showRisk(p.simulation);
  } else {
    simulationDirty = false;
    by("risk-output").replaceChildren();
    el(
      by("risk-output"),
      "p",
      "Run a simulation for this calculation.",
      "empty",
    );
  }
}
async function calculate({ save = false, simulation = null } = {}) {
  clearTimeout(timer);
  if (!currentCase) throw Error("Load a case first.");
  if (by("input").value !== JSON.stringify(currentCase, null, 2))
    throw Error("Apply the edited JSON before calculating or saving.");
  const payload = structuredClone(currentCase),
    rev = revision,
    id = ++requestNumber;
  status(simulation ? "Running the risk simulation…" : "Calculating…");
  const p = await (
    await api("/api/v1/analysis", { case: payload, save, simulation })
  ).json();
  if (rev !== revision || id !== requestNumber) return;
  show(p);
  status(
    save
      ? "Research run saved. Attach source evidence in Evidence & review."
      : "Calculated. Review assumptions and evidence before use.",
  );
  if (save) await loadHistory();
}
async function loadExample() {
  invalidate();
  currentCase = await (await api("/api/v1/example")).json();
  syncControls();
  await calculate();
}
by("sample").onclick = () => guarded(loadExample);
by("run").onclick = () => guarded(() => calculate());
by("save").onclick = () =>
  guarded(() => {
    if (simulationDirty)
      throw Error(
        "Simulation settings changed. Run the simulation before saving its results.",
      );
    return calculate({
      save: true,
      simulation: packet?.simulation?.settings || null,
    });
  });
by("apply-json").onclick = () =>
  guarded(async () => {
    const parsed = JSON.parse(by("input").value);
    await api("/api/v1/valuation", parsed);
    invalidate();
    currentCase = parsed;
    syncControls();
    await calculate();
  });
by("upload").onchange = () =>
  guarded(async () => {
    const f = by("upload").files[0];
    if (!f) return;
    if (f.size > 262144) throw Error("Case exceeds 256 KB.");
    invalidate();
    by("input").value = await f.text();
    status("Imported JSON. Apply JSON to validate it.");
  });
by("chart-metric").onchange = forecastChart;
for (const mode of ["guided", "advanced"])
  by(mode).onclick = () => {
    document.body.classList.toggle("advanced", mode === "advanced");
    by("guided").setAttribute("aria-pressed", String(mode === "guided"));
    by("advanced").setAttribute("aria-pressed", String(mode === "advanced"));
  };
document.querySelectorAll("[data-tab]").forEach(
  (b) =>
    (b.onclick = () => {
      document
        .querySelectorAll(".view")
        .forEach((v) => (v.hidden = v.id !== b.dataset.tab));
      document
        .querySelectorAll("[data-tab]")
        .forEach((n) => n.removeAttribute("aria-current"));
      b.setAttribute("aria-current", "page");
      if (b.dataset.tab === "workflow") guarded(loadHistory);
      if (b.dataset.tab === "valuation") forecastChart();
      if (b.dataset.tab === "risk" && packet?.simulation && !simulationDirty)
        showRisk(packet.simulation);
    }),
);
function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
by("download").onclick = () =>
  download(
    new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" }),
    "valuation-research.json",
  );
exports.forEach(
  (b) =>
    (b.onclick = () =>
      guarded(async () => {
        const response = await api(
          "/api/v1/export/" + b.dataset.kind,
          completedCase,
        );
        download(await response.blob(), "valuation." + b.dataset.kind);
      })),
);
function showRisk(s) {
  const root = by("risk-output");
  root.replaceChildren();
  if (s.status !== "ok") {
    el(root, "p", s.reason, "empty");
    return;
  }
  const strip = el(root, "div", "", "value-strip");
  metrics(strip, [
    ["5th percentile / share", fmt(s.p05), "Lower modeled outcome"],
    [
      "Median / share",
      fmt(s.p50),
      `${s.accepted} accepted of ${s.requested} draws`,
    ],
    ["95th percentile / share", fmt(s.p95), "Upper modeled outcome"],
  ]);
  el(
    root,
    "p",
    `Rejected: ${s.rejected} (${pct(s.rejection_rate)}). Financing gaps: ${pct(s.financing_gap_probability)}. Conditional on accepted draws. ${s.settings.source}`,
    "small",
  );
  const chart = el(root, "div", "", "chart");
  const width = Math.max(320, chart.clientWidth || 820),
    left = 45,
    right = width - 20,
    binWidth = (right - left) / s.histogram.length;
  const svg = svgNode(chart, "svg", {
    viewBox: `0 0 ${width} 240`,
    role: "img",
    "aria-label":
      "Histogram of modeled per-share values. Counts and bin limits in the distribution table.",
  });
  const max = Math.max(...s.histogram.map((x) => x.count), 1);
  svgNode(svg, "text", { x: left, y: 14 }, "Draws");
  [0, 0.5, 1].forEach((f) => {
    const y = 195 - f * 170;
    svgNode(svg, "line", { x1: left, x2: right, y1: y, y2: y, class: "axis" });
    svgNode(
      svg,
      "text",
      { x: left - 7, y: y + 4, "text-anchor": "end" },
      String(Math.round(max * f)),
    );
  });
  s.histogram.forEach((b, i) => {
    const h = (b.count / max) * 170;
    const rect = svgNode(svg, "rect", {
      x: left + i * binWidth,
      y: 195 - h,
      width: Math.max(2, binWidth - 3),
      height: h,
      fill: "#327763",
      tabindex: 0,
      "aria-label": `${fmt(b.low)} to ${fmt(b.high)}: ${b.count} draws`,
    });
    svgNode(rect, "title", {}, `${fmt(b.low)}–${fmt(b.high)}: ${b.count}`);
  });
  svgNode(svg, "text", { x: left, y: 220 }, fmt(s.histogram[0].low));
  svgNode(
    svg,
    "text",
    { x: right, y: 220, "text-anchor": "end" },
    fmt(s.histogram.at(-1).high),
  );
  svgNode(
    svg,
    "text",
    { x: width / 2, y: 238, "text-anchor": "middle" },
    "Per-share value · " + completedCase.currency,
  );
  el(root, "h3", "FCFF uncertainty through time");
  el(
    root,
    "p",
    "5th–95th percentile band and median · " +
      completedCase.currency +
      " millions",
    "small",
  );
  const fan = el(root, "div", "", "chart");
  lineChart(
    fan,
    [
      {
        name: "Median FCFF",
        values: s.fan.map((x) => x.p50),
        color: "#176854",
      },
    ],
    s.fan.map((x) => "Y" + x.year),
    "FCFF 5th–95th percentile band in currency millions; not a confidence interval.",
    { band: { low: s.fan.map((x) => x.p05), high: s.fan.map((x) => x.p95) } },
  );
  const detail = el(root, "details");
  el(detail, "summary", "Distribution, fan and downside data");
  const hist = el(detail, "div", "", "scroll");
  table(
    hist,
    ["Bin low", "Bin high", "Draws"],
    s.histogram.map((x) => [fmt(x.low), fmt(x.high), x.count]),
  );
  const fanTable = el(detail, "div", "", "scroll");
  table(
    fanTable,
    ["Year", "FCFF p05", "FCFF p50", "FCFF p95"],
    s.fan.map((x) => [x.year, fmt(x.p05), fmt(x.p50), fmt(x.p95)]),
  );
  el(
    detail,
    "p",
    `Below reference price: ${pct(s.probability_below_price)}. Loss VaR 95%: ${fmt(s.loss_var95)}. Expected shortfall 95%: ${fmt(s.loss_expected_shortfall95)}. Lower-tail mean value: ${fmt(s.lower_tail_mean)}. Loss measures require a reference share price.`,
  );
}
by("risk-form").onsubmit = (e) => {
  e.preventDefault();
  guarded(() =>
    calculate({
      simulation: {
        draws: Number(by("draws").value),
        seed: Number(by("seed").value),
        growth_sd: Number(by("growth-sd").value) / 100,
        margin_sd: Number(by("margin-sd").value) / 100,
        wacc_sd: Number(by("wacc-sd").value) / 100,
        reference_price: by("reference-price").value
          ? Number(by("reference-price").value)
          : null,
        correlation: JSON.parse(by("correlation").value),
      },
    }),
  );
};
by("macro-form").onsubmit = (e) => {
  e.preventDefault();
  guarded(async () => {
    const rev = revision;
    const p = await (
      await api("/api/v1/macro", {
        case: currentCase,
        shock: {
          real_growth_delta_pp: Number(by("gdp-shock").value),
          inflation_delta_pp: Number(by("inflation-shock").value),
          policy_rate_delta_pp: Number(by("rate-shock").value),
          fx_depreciation_pct: Number(by("fx-shock").value),
          revenue_gdp_beta: Number(by("gdp-beta").value),
          pricing_pass_through: Number(by("price-pass").value),
          import_cost_share: Number(by("import-share").value),
          rate_pass_through: Number(by("rate-pass").value),
          source: "Interactive analyst-specified macro scenario",
        },
      })
    ).json();
    if (rev !== revision) return;
    by("macro-result").textContent =
      `Macro DCF / share: ${fmt(p.result.base.per_share)}. Growth shift ${pct(p.transmission.revenue_growth_delta)}, margin shift ${pct(p.transmission.margin_delta)}, financing-rate shift ${pct(p.transmission.rate_delta)}. ${p.assumptions}`;
  }, by("macro-result"));
};
const methodExamples = {
  "capital-cost": {
    risk_free: 0.08,
    equity_risk_premium: 0.055,
    unlevered_beta: 0.9,
    debt_weight: 0.25,
    tax_rate: 0.27,
    pretax_cost_debt: 0.11,
    country_premium: 0.02,
    country_exposure: 1,
    source: "Fictional calibration; replace with dated evidence",
  },
  liability: {
    payments: [100000, 100000, 100000, 100000, 100000],
    survival: [0.99, 0.98, 0.965, 0.95, 0.93],
    spot_rates: [0.07, 0.075, 0.08, 0.082, 0.085],
    source: "Fictional survival and spot-curve assumptions",
  },
};
const methodHelp = {
  "capital-cost":
    "Relever operating beta using target market-value capital weights. Review country-risk overlap and tax-shield usability. These fictional inputs are not market data.",
  fcfe: "Supply cash flows after interest and net borrowing, discounted at cost of equity. The terminal cash flow is the first one AFTER the forecast. Do not subtract debt again.",
  dividends:
    "Supply sustainable equity distributions and a cost of equity. The terminal dividend is the first one AFTER the explicit forecast.",
  residual_income:
    "Supply residual earnings: net income minus cost of equity times opening book equity. Add adjusted opening book equity. Continuing residual income must be supplied explicitly.",
  apv: "Supply unlevered cash flows and their discount rate, plus one tax shield per period and a separate tax-shield rate. Terminal tax shields are excluded. Result is enterprise value.",
  liability:
    "Supply end-year benefits, unconditional survival probabilities and annual effective spot rates. No death benefit, expense loading, lapse model or regulatory risk margin is included.",
};
function chooseMethod() {
  const method = by("method-choice").value;
  by("method-chart").replaceChildren();
  let sample = methodExamples[method];
  if (method === "reverse-dcf")
    sample = {
      case: currentCase,
      market_price: 25,
      driver: "revenue_growth",
      lower: -0.1,
      upper: 0.5,
    };
  if (method === "earnings-quality")
    sample = {
      net_income: 20000000,
      operating_cash_flow: 15000000,
      opening_assets: 90000000,
      closing_assets: 110000000,
      revenue: 120000000,
      previous_revenue: 110000000,
      receivables: 18000000,
      previous_receivables: 14000000,
      stock_compensation: 2000000,
      capex: 6000000,
      source: "Fictional annual comparison",
    };
  if (method === "forecast-evaluation")
    sample = {
      bars: Array.from({ length: 40 }, (_, i) => ({
        date: new Date(Date.UTC(2020, 0, i + 1)).toISOString().slice(0, 10),
        open: 100 + i,
        high: 101 + i,
        low: 99 + i,
        close: 100 + i,
        volume: 1000,
      })),
      minimum_train: 20,
      horizon: 5,
      model: "ar1",
      source: "Synthetic trend; not market performance",
      adjustment: "unadjusted",
    };
  if (!sample)
    sample = {
      method,
      cashflows: method === "residual_income" ? [5, 6, 7] : [10, 12, 14],
      discount_rate: 0.12,
      terminal_growth: 0.03,
      terminal_cashflow: method === "residual_income" ? 0 : 14.42,
      opening_book_equity: method === "residual_income" ? 100 : 0,
      tax_shields: method === "apv" ? [1, 1, 1] : [],
      tax_shield_rate: 0.08,
      distress_cost_pv: 0,
      source: "Fictional cash flows; same currency and unit throughout",
    };
  by("method-input").value = JSON.stringify(sample, null, 2);
  by("method-help").textContent = methodHelp[method];
  by("method-output").textContent =
    "Ready to calculate. Replace fictional inputs with sourced assumptions.";
}
by("method-choice").onchange = chooseMethod;
by("calculate-method").onclick = () =>
  guarded(async () => {
    const name = by("method-choice").value;
    const research = [
      "reverse-dcf",
      "earnings-quality",
      "forecast-evaluation",
    ].includes(name);
    const route = research
      ? name
      : ["capital-cost", "liability"].includes(name)
        ? name
        : "cashflows";
    const result = await (
      await api(
        (research ? "/api/v1/research/" : "/api/v1/methods/") + route,
        JSON.parse(by("method-input").value),
      )
    ).json();
    by("method-output").textContent = JSON.stringify(result, null, 2);
    if (name === "forecast-evaluation") {
      const values = result.folds.flatMap((x) => x.actual),
        pred = result.folds.flatMap((x) => x.predicted),
        base = result.folds.flatMap((x) => x.random_walk);
      lineChart(
        by("method-chart"),
        [
          { name: "Actual", values, color: "#18352f" },
          { name: "Forecast", values: pred, color: "#176854" },
          { name: "Random walk", values: base, color: "#a64d29", dashed: true },
        ],
        values.map((_, i) => (i % 5 === 0 ? "T" + (i + 1) : "")),
        "Held-out actual and forecast closes. Exact values in the calculation record.",
        { scale: 1 },
      );
    }
  }, by("method-output"));
async function loadKnowledge(init = false) {
  const id = ++searchNumber;
  const q = new URLSearchParams({
    q: by("knowledge-query").value,
    domain: by("knowledge-domain").value,
  });
  const p = await (await api("/api/v1/knowledge?" + q)).json();
  if (id !== searchNumber) return;
  if (init) {
    [...new Set(p.skills.map((s) => s.domain))].sort().forEach((d) => {
      const option = el(by("knowledge-domain"), "option", title(d));
      option.value = d;
    });
  }
  by("knowledge-meta").textContent =
    `${p.skills.length} matching methods · ${p.sources.length} primary sources · version ${p.version}. Original summaries, not licensed curriculum content.`;
  const root = by("knowledge-results");
  root.replaceChildren();
  if (!p.skills.length)
    el(
      root,
      "p",
      "No methods match. Try fewer terms or another discipline.",
      "empty",
    );
  for (const s of p.skills) {
    const row = el(root, "article", "", "knowledge-item");
    const meta = el(row, "div", "", "domain");
    el(meta, "span", title(s.domain));
    el(meta, "br");
    el(meta, "span", s.status, "state");
    const body = el(row, "div");
    el(body, "h3", s.title);
    el(body, "p", s.formula);
    el(body, "p", "Preconditions: " + s.assumptions);
    const details = el(body, "details");
    el(details, "summary", "Validation & failure conditions");
    el(details, "p", s.validation);
    el(details, "p", s.failure_modes);
    for (const id of s.source_ids) {
      const source = p.sources.find((x) => x.id === id);
      const a = el(
        body,
        "a",
        source.publisher + " · " + (source.publication_date || "undated"),
      );
      a.href = source.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    el(body, "br");
    const button = el(body, "button", "Read full skill");
    button.onclick = () =>
      guarded(async () => {
        const data = await (
          await api("/api/v1/knowledge/" + encodeURIComponent(s.id))
        ).json();
        by("skill-text").textContent = data.markdown;
        by("skill-detail").open = true;
        by("skill-detail").scrollIntoView({ block: "start" });
      });
  }
}
by("knowledge-query").oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => guarded(() => loadKnowledge()), 200);
};
by("knowledge-domain").onchange = () => guarded(() => loadKnowledge());
by("data-form").onsubmit = (e) => {
  e.preventDefault();
  guarded(async () => {
    by("data-status").textContent = "Fetching official observations…";
    by("data-table").replaceChildren();
    const q = new URLSearchParams({
      country: by("data-country").value,
      indicator: by("data-indicator").value,
      start: by("data-start").value,
      end: by("data-end").value,
    });
    const p = await (await api("/api/v1/data/world-bank?" + q)).json();
    by("data-status").textContent =
      `${p.provider} · retrieved ${p.retrieved_at} · SHA-256 ${p.sha256.slice(0, 12)}. ${p.vintage_warning}`;
    table(
      by("data-table"),
      ["Year", "Observation", "Unit"],
      p.observations.map((x) => [
        x.year,
        x.value == null ? "Missing" : fmt(x.value),
        x.unit,
      ]),
    );
  }, by("data-status"));
};
async function loadHistory() {
  const list = await (await api("/api/v1/runs")).json();
  by("history").replaceChildren();
  if (!list.length) el(by("history"), "p", "No saved runs yet.", "empty");
  list.forEach((r) => {
    const b = el(
      by("history"),
      "button",
      new Date(r.created_at).toLocaleString() +
        " · " +
        r.input_hash.slice(0, 10),
      "history-item",
    );
    b.onclick = () => guarded(() => loadRun(r.id));
  });
}
async function loadRun(id) {
  const r = await (await api("/api/v1/runs/" + id)).json();
  invalidate();
  currentCase = r.payload.result.inputs;
  syncControls();
  show({ ...r.payload, run_id: id, workflow: r.workflow });
  renderEvidence(r.evidence);
  status(
    "Loaded saved run " + id.slice(0, 8) + ". Edits create a new research run.",
  );
}
function renderEvidence(records) {
  by("evidence-list").replaceChildren();
  for (const r of records) {
    const item = el(by("evidence-list"), "div", "", "evidence-item");
    el(item, "strong", r.input_path + " · " + r.review);
    el(item, "p", r.claim);
    const a = el(item, "a", r.publisher + " · " + r.published_date);
    a.href = r.source_url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    el(item, "p", r.notes);
  }
}
by("refresh-history").onclick = () => guarded(loadHistory);
by("evidence-form").onsubmit = (e) => {
  e.preventDefault();
  guarded(async () => {
    if (!runId) throw Error("Save a run first.");
    const id = runId;
    await api("/api/v1/runs/" + id + "/evidence", {
      claim: by("evidence-claim").value,
      input_path: by("evidence-path").value,
      source_url: by("evidence-url").value,
      publisher: by("evidence-publisher").value,
      published_date: by("evidence-date").value,
      retrieved_date: by("evidence-retrieved").value,
      period: by("evidence-period").value,
      units: by("evidence-units").value,
      locator: by("evidence-locator").value,
      kind: by("evidence-kind").value,
      review: by("evidence-review").value,
      notes: by("evidence-notes").value,
    });
    if (runId === id) await loadRun(id);
  });
};
chooseMethod();
guarded(loadExample);
guarded(() => loadKnowledge(true));
guarded(loadRepositories);

function syncRiskSettings(s) {
  for (const [id, key, mult] of [
    ["draws", "draws", 1],
    ["seed", "seed", 1],
    ["growth-sd", "growth_sd", 100],
    ["margin-sd", "margin_sd", 100],
    ["wacc-sd", "wacc_sd", 100],
  ])
    by(id).value = s[key] * mult;
  by("reference-price").value = s.reference_price ?? "";
  by("correlation").value = JSON.stringify(s.correlation);
}
by("risk-form").addEventListener("input", () => {
  if (!packet?.simulation) return;
  simulationDirty = true;
  let notice = by("risk-stale");
  if (!notice) {
    notice = document.createElement("p");
    notice.id = "risk-stale";
    notice.className = "stale";
    notice.setAttribute("role", "status");
    by("risk-output").prepend(notice);
  }
  notice.textContent =
    "Simulation settings changed. This distribution shows the previous settings. Rerun before saving.";
});
by("macro-form").addEventListener("input", () => {
  by("macro-result").textContent =
    "Scenario settings changed. Evaluate again for current assumptions.";
});
by("method-input").addEventListener("input", () => {
  by("method-output").textContent =
    "Inputs changed. Calculate again to update the result.";
});
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (!by("valuation").hidden) forecastChart();
    if (!by("risk").hidden && packet?.simulation && !simulationDirty)
      showRisk(packet.simulation);
  }, 150);
});

methodHelp["reverse-dcf"] =
  "Solve the growth, margin or WACC consistent with a supplied market price. Search bounds are explicit. This reveals model-implied expectations, not a forecast.";
methodHelp["earnings-quality"] =
  "Compare annual earnings with cash generation and receivable days before valuation. Screening flags require investigation and do not establish fraud.";
methodHelp["forecast-evaluation"] =
  "Evaluate synthetic or supplied OHLCV using expanding training windows and non-overlapping holdouts. Compare against a random walk. Kronos is an optional Python adapter, not installed weights.";
by("instrument-form").onsubmit = (e) => {
  e.preventDefault();
  guarded(async () => {
    by("instrument-status").textContent =
      "Searching the pinned security master…";
    const q = new URLSearchParams({
      q: by("instrument-query").value,
      exchange: by("instrument-exchange").value,
      country: by("instrument-country").value,
    });
    const data = await (await api("/api/v1/instruments?" + q)).json();
    by("instrument-status").textContent = data.total_loaded
      ? `${data.total_loaded.toLocaleString()} listings loaded · showing ${data.results.length} matches (maximum 50) · revision ${data.source_commit.slice(0, 10)}. ZAC means cents; preserve quote units.`
      : "No universe imported. Run python scripts/ingest_instruments.py in the project.";
    table(
      by("instrument-table"),
      ["Symbol", "Name", "Exchange", "Currency", "Sector"],
      data.results.map((x) => [
        x.symbol,
        x.name,
        x.exchange,
        x.currency,
        x.sector,
      ]),
    );
  }, by("instrument-status"));
};
async function loadRepositories() {
  const data = await (await api("/api/v1/repositories")).json();
  const t = table(
    by("repository-table"),
    ["Repository", "Code license", "Decision"],
    data.map((x) => [x.repo, x.license, x.integration]),
  );
  [...t.tBodies[0].rows].forEach((row, i) => {
    row.cells[0].replaceChildren();
    const a = el(row.cells[0], "a", data[i].repo);
    a.href = data[i].url + "/tree/" + data[i].commit;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
  });
}
by("prepare-research").onclick = () =>
  guarded(async () => {
    if (!completedCase || !by("stale").hidden)
      throw Error(
        "Calculate the current case before preparing a research plan.",
      );
    const data = await (
      await api("/api/v1/research/plan", completedCase)
    ).json();
    by("research-roles").replaceChildren();
    for (const role of data.roles) {
      const row = el(by("research-roles"), "article", "", "knowledge-item");
      const meta = el(row, "div", role.role, "domain");
      el(meta, "span", title(role.state), "state");
      const body = el(row, "div");
      el(body, "p", role.finding);
      const list = el(body, "ul");
      role.required.forEach((x) => el(list, "li", x));
      el(body, "p", "Available tools: " + role.tools.join(", "), "small");
    }
  });
