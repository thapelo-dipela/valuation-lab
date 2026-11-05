"""Optional browser check. pip install playwright; playwright install chromium."""

from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import os

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".impeccable" / "review"
OUT.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("VALUATION_URL", "http://127.0.0.1:8018")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
    )
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE)
    page.wait_for_function(
        "document.querySelector('#status').textContent.startsWith('Calculated.')"
    )
    assert page.locator("#metrics .value-item").count() == 3
    baseline = page.locator("#metrics strong").first.inner_text()
    page.locator("#revenue_growth").fill("10")
    page.wait_for_function(
        "document.querySelector('#stale').hidden && document.querySelector('#status').textContent.startsWith('Calculated.')"
    )
    assert page.locator("#metrics strong").first.inner_text() != baseline
    page.locator("#sensitivity button").first.click()
    page.wait_for_function("document.querySelector('#stale').hidden")
    page.locator("#sample").click()
    page.wait_for_function(
        "document.querySelector('#status').textContent.startsWith('Calculated.')"
    )
    page.screenshot(path=str(OUT / "desktop.png"), full_page=True)
    page.locator('[data-tab="risk"]').click()
    page.locator("#draws").fill("200")
    page.locator("#risk-form button").click()
    page.wait_for_selector("#risk-output svg")
    assert "accepted of 200" in page.locator("#risk-output").inner_text()
    page.locator("#draws").fill("300")
    assert page.locator("#risk-stale").is_visible()
    page.locator("#save").click()
    page.wait_for_function(
        "document.querySelector('#status').textContent.includes('Run the simulation before saving')"
    )
    page.locator("#risk-form button").click()
    page.wait_for_function(
        "document.querySelector('#risk-output').textContent.includes('accepted of 300')"
    )
    assert page.locator("#risk-stale").count() == 0
    page.locator("#macro-form button").click()
    page.wait_for_function(
        "document.querySelector('#macro-result').textContent.includes('Macro DCF')"
    )
    page.screenshot(path=str(OUT / "risk.png"), full_page=True)
    page.locator('[data-tab="methods"]').click()
    for name in [
        "capital-cost",
        "fcfe",
        "residual_income",
        "apv",
        "dividends",
        "liability",
        "reverse-dcf",
        "earnings-quality",
        "forecast-evaluation",
    ]:
        page.locator("#method-choice").select_option(name)
        page.locator("#calculate-method").click()
        page.wait_for_function(
            "document.querySelector('#method-output').textContent.startsWith('{')"
        )
    page.locator('[data-tab="knowledge"]').click()
    page.locator("#instrument-query").fill("Sasol")
    page.locator("#instrument-form button").click()
    page.wait_for_function(
        "document.querySelector('#instrument-status').textContent.includes('listings loaded')"
    )
    assert "SOL.JO" in page.locator("#instrument-table").inner_text()
    page.locator("#knowledge-query").fill("survival")
    page.wait_for_function(
        "document.querySelector('#knowledge-meta').textContent.startsWith('2 matching') || document.querySelector('#knowledge-results').textContent.includes('Survival-contingent liability')"
    )
    page.locator("#knowledge-domain").select_option("actuarial-risk")
    page.locator("#knowledge-results button").first.click()
    page.wait_for_function(
        "document.querySelector('#skill-text').textContent.includes('Output contract')"
    )
    page.locator("#save").click()
    page.wait_for_function(
        "document.querySelector('#status').textContent.startsWith('Research run saved')"
    )
    page.locator('[data-tab="workflow"]').click()
    page.locator("#prepare-research").click()
    page.wait_for_selector("#research-roles article")
    assert page.locator("#research-roles article").count() == 7
    page.wait_for_selector(".history-item")
    assert page.locator("#add-evidence").is_enabled()
    page.locator("#evidence-claim").fill("Browser smoke test evidence")
    page.locator("#evidence-url").fill("https://example.com/report")
    page.locator("#evidence-publisher").fill("Synthetic browser test")
    page.locator("#evidence-date").fill("2026-01-01")
    page.locator("#evidence-retrieved").fill("2026-11-04")
    page.locator("#evidence-period").fill("FY2025")
    page.locator("#evidence-units").fill("ZAR")
    page.locator("#evidence-locator").fill("page 1")
    page.locator("#evidence-kind").select_option("synthetic")
    page.locator("#add-evidence").click()
    page.wait_for_selector(".evidence-item")
    page.locator("#advanced").click()
    page.locator(".controls details").evaluate("e => e.open = true")
    original = page.locator("#input").input_value()
    page.locator("#input").fill("{invalid")
    page.locator("#apply-json").click()
    page.wait_for_function(
        "document.querySelector('#status').classList.contains('error')"
    )
    assert page.locator("#download").is_disabled()
    page.locator("#input").fill(original)
    page.locator("#apply-json").click()
    page.wait_for_function(
        "document.querySelector('#status').textContent.startsWith('Calculated.')"
    )
    page.locator("#guided").click()
    page.locator('[data-tab="valuation"]').click()
    with page.expect_download() as dl:
        page.locator('[data-kind="xlsx"]').click()
    assert dl.value.suggested_filename == "valuation.xlsx"
    mobile = browser.new_page(
        viewport={"width": 390, "height": 844}, reduced_motion="reduce"
    )
    mobile.goto(BASE)
    mobile.wait_for_function(
        "document.querySelector('#status').textContent.startsWith('Calculated.')"
    )
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.screenshot(path=str(OUT / "mobile.png"), full_page=True)
    mobile.locator('[data-tab="risk"]').click()
    mobile.locator("#draws").fill("100")
    mobile.locator("#risk-form button").click()
    mobile.wait_for_selector("#risk-output svg")
    mobile.screenshot(path=str(OUT / "mobile-risk.png"), full_page=True)
    assert not errors, errors
    print(
        json.dumps(
            {
                "desktop": "passed",
                "mobile": "passed",
                "javascript_errors": errors,
                "screenshots": str(OUT),
            }
        )
    )
    browser.close()
