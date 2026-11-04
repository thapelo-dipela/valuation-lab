"""Generate original, editable deliverables from a valuation result."""
from io import BytesIO

from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from pptx import Presentation

GROUPS = {
    "Income statement": ("revenue", "ebitda", "depreciation", "ebit", "interest", "pretax", "tax", "net_income"),
    "Balance sheet": ("cash", "receivables", "inventory", "ppe", "assets", "payables", "debt", "equity", "funding"),
    "Cash flow": ("net_income", "depreciation", "change_nwc", "cfo", "cfi", "cff", "change_cash", "fcff"),
}
NOTICE = "Illustrative management forecast. Review data, assumptions and financing before use."


def summary(result):
    currency = result["inputs"]["currency"]
    lines = []
    for label, key in (("Base DCF", "base"), ("ESG / macro scenario", "scenario"), ("Trading comparables", "comps")):
        estimate = result[key]
        share = estimate.get("per_share")
        lines.append(f"{label}: {currency} {share:,.2f} per diluted share" if share is not None
                     else f"{label}: {estimate.get('reason', 'Unavailable')}")
    return lines


def render(kind, result):
    data = result["inputs"]
    identity = f"{data['valuation_date']} | {data['currency']} | Model {result['version']}"
    fingerprint = result["input_sha256"]
    risks = [f"{r['factor'].title()}: {r['issue']} | {r['driver']} {r['change_pp']:+g} pp, "
             f"years {r['start']}–{r['end']} | {r['confidence']} confidence | {r['source']}"
             for r in data["risks"]]
    if kind == "docx":
        file = Document()
        file.add_heading(data["company"], 0)
        file.add_paragraph(f"Valuation memorandum | {identity}")
        file.add_paragraph(NOTICE)
        for title, lines in (
            ("Valuation indications", summary(result)),
            ("Assumptions and sources", [data["opening"]["source"], data["drivers"]["source"]] +
             [f"{k}: {v:.2%}" for k, v in data["drivers"].items() if k != "source"] +
             [f"{p['name']}: {p['source']}" for p in data["peers"]]),
            ("ESG and macro scenario", risks or ["No adjustments supplied"]),
            ("Review flags", result["checks"] or ["No flags from implemented checks"]),
            ("Reproducibility", [f"Input SHA-256: {fingerprint}"]),
        ):
            file.add_heading(title, level=1)
            for line in lines:
                file.add_paragraph(line, style="List Bullet")
    elif kind == "pptx":
        file = Presentation()
        slide = file.slides.add_slide(file.slide_layouts[0])
        slide.shapes.title.text = data["company"]
        slide.placeholders[1].text = f"Valuation briefing\n{identity}"
        sections = [("Valuation indications", summary(result)), ("Model drivers", [
            f"WACC {data['drivers']['wacc']:.1%}",
            f"Terminal growth {data['drivers']['terminal_growth']:.1%}",
            f"Terminal ROIC {data['drivers']['terminal_roic']:.1%}",
        ]), ("ESG and macro", [f"{r['factor'].title()} | {r['driver']} {r['change_pp']:+g} pp, "
            f"years {r['start']}–{r['end']}" for r in data["risks"]]),
            ("Review flags", result["checks"]), ("Model record", [NOTICE, f"Input SHA-256 {fingerprint}"])]
        for title, lines in sections:
            lines = lines or ["None supplied"]
            for start in range(0, len(lines), 5):
                slide = file.slides.add_slide(file.slide_layouts[1])
                slide.shapes.title.text = title if start == 0 else f"{title} (continued)"
                slide.placeholders[1].text = "\n".join(lines[start:start+5])
    else:
        file = Workbook()
        meta = file.active
        meta.title = "Model record"
        for line in [data["company"], identity, NOTICE, fingerprint, *summary(result), *risks, *result["checks"]]:
            cell = meta.cell(meta.max_row + 1, 1, line)
            cell.data_type = "s"
        meta.column_dimensions["A"].width = 95
        for prefix, key in (("Base", "statements"), ("Scenario", "scenario_statements")):
            for group, fields in GROUPS.items():
                ws = file.create_sheet(f"{prefix} {group}")
                rows = result[key]
                ws.append([data["currency"], *(f"Year {r['year']}" for r in rows)])
                for field in fields:
                    ws.append([field.replace("_", " ").title(), *(r[field] for r in rows)])
                ws.freeze_panes = "B2"
                ws.column_dimensions["A"].width = 24
                for column in list(ws.columns)[1:]:
                    ws.column_dimensions[column[0].column_letter].width = 19
                    for cell in column[1:]:
                        cell.number_format = "#,##0.00;[Red](#,##0.00)"
                for cell in ws[1]:
                    cell.fill = PatternFill("solid", fgColor="172D44")
                    cell.font = Font(color="FFFFFF", bold=True)
    output = BytesIO()
    file.save(output)
    return output.getvalue()
