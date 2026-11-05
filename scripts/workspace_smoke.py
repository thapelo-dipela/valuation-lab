import os
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(".impeccable/review")
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(os.environ.get("VALUATION_URL", "http://127.0.0.1:8018"))
    page.wait_for_selector("#account-table table")
    page.wait_for_function(
        "document.querySelector('#status').textContent.startsWith('Calculated.')"
    )
    print("errors", errors)
    print("status", page.locator("#status").inner_text())
    page.screenshot(path=str(out / "desktop.png"), full_page=True)
    page.locator('.tabs [data-tab="market"]').click()
    page.screenshot(path=str(out / "market.png"), full_page=True)
    page.locator('.tabs [data-tab="methods"]').click()
    page.screenshot(path=str(out / "methods.png"), full_page=True)
    page.locator("#calculate-method").click()
    page.wait_for_timeout(600)
    print("method", page.locator("#method-results").inner_text()[:250])
    page.locator('.tabs [data-tab="projections"]').click()
    print("forecast inputs", page.locator("[data-year]").count())
    page.locator('[data-driver="revenue_growth"][data-year="0"]').fill("12")
    page.get_by_role("button", name="Apply forecast", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#status').textContent.startsWith('Calculated.') && document.querySelector('#stale').hidden"
    )
    assert page.evaluate("currentCase.annual_drivers[0].revenue_growth") == 0.12
    page.locator("#projection-view").select_option("income")
    assert "134,400,000" in page.locator("#projection-table").inner_text()
    page.locator('.tabs [data-tab="accounting"]').click()
    page.get_by_role("button", name="Edit statements", exact=True).click()
    page.get_by_label("2025 Revenue", exact=True).fill("130000000")
    page.get_by_role("button", name="Save statement edits", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#account-status').textContent.includes('saved to the local database')"
    )
    assert page.evaluate("accountResult.rows.at(-1).revenue") == 130000000
    page.get_by_role("button", name="Use latest year in valuation", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#account-status').textContent.includes('now drive')"
    )
    assert page.evaluate("currentCase.opening.revenue") == 130000000
    page.locator("#reporting-currency").select_option("USD")
    page.wait_for_function("accountResult.currency === 'USD'")
    page.locator('.tabs [data-tab="market"]').click()
    assert "Not comparable" in page.locator("#share-models").inner_text()
    page.locator('.tabs [data-tab="accounting"]').click()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(out / "mobile.png"), full_page=True)
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    assert not errors, errors
    print("Desktop/mobile accounting, forecast, currency mismatch: pass")
    b.close()
