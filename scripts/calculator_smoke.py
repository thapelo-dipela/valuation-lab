import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(os.environ.get("VALUATION_URL", "http://127.0.0.1:8018"))
    page.wait_for_selector("#account-table table")
    page.wait_for_function("!!packet")
    page.locator('.tabs [data-tab="methods"]').click()
    names = page.locator("#method-choice option").evaluate_all(
        "(nodes)=>nodes.map(n=>n.value)"
    )
    for name in names:
        page.locator("#method-choice").select_option(name)
        page.locator("#calculate-method").click()
        page.wait_for_function(
            "document.querySelector('#method-results').textContent!=='Calculating…'"
        )
        result = page.locator("#method-results").inner_text()
        assert len(result) > 30, (name, result)
        assert "detail" not in result[:20], (name, result)
        print(name, "ok")
    page.locator('.tabs [data-tab="accounting"]').click()
    page.locator("#display-currency").select_option("USD")
    page.get_by_role("button", name="Convert display", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#fx-status').textContent.includes('ECB')"
    )
    assert page.evaluate("fx.rate > 0 and fx.rate < 1".replace(" and ", " && "))
    assert "USD" in page.locator("#account-table").inner_text()
    page.get_by_role("button", name="Edit statements", exact=True).click()
    assert "ZAR" in page.locator("#account-table thead").inner_text()
    gross = (
        page.locator("#account-table tr")
        .filter(has=page.get_by_role("rowheader", name="Gross profit", exact=True))
        .inner_text()
    )
    assert "50,400,000" in gross, gross
    page.screenshot(path=".impeccable/review/fx-edit.png", full_page=True)
    page.get_by_role("button", name="Edit statements", exact=True).click()
    page.locator('.tabs [data-tab="market"]').click()
    assert "USD" in page.locator("#share-models").inner_text()
    page.locator("#quote-currency").select_option("ZAC")
    assert (
        page.evaluate('document.querySelector("#market-facts strong").textContent')
        != "26.55"
    )
    page.locator('.tabs [data-tab="accounting"]').click()
    page.evaluate(
        """() => { const original = window.fetch; window.fetch = (url, options) => String(url).includes('/api/v1/fx?') ? new Promise(resolve => { window.finishOldQuote = () => resolve(new Response(JSON.stringify({base:'ZAR',quote:'USD',rate:0.06,date:'2026-11-04',source:'Test'}),{status:200,headers:{'Content-Type':'application/json'}})); }) : original(url,options); }"""
    )
    page.get_by_role("button", name="Convert display", exact=True).click()
    page.locator("#reporting-currency").select_option("EUR")
    page.evaluate("window.finishOldQuote()")
    page.wait_for_function(
        "document.querySelector('#fx-status').textContent.includes('while fetching')"
    )
    assert page.evaluate('fx.rate === 1 && fx.quote === "EUR"')
    page.get_by_role("button", name="Use latest year in valuation", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#account-status').textContent.includes('Previous-currency')"
    )
    assert page.evaluate(
        'currentCase.currency === "EUR" && currentCase.opening.excess_cash === 0 && currentCase.peers.length === 0'
    )
    assert not errors, errors
    print("live FX, cents quote, all nine calculators: pass")
    browser.close()
