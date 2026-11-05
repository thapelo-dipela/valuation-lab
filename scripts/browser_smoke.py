"""Desktop/mobile workflow and calculator smoke tests. Requires Playwright Chromium.
Run against a running app; VALUATION_URL defaults to http://127.0.0.1:8018.
The calculator smoke includes a live ECB/Frankfurter connectivity check.
"""

from pathlib import Path
import runpy

for script in ("workspace_smoke.py", "calculator_smoke.py"):
    runpy.run_path(str(Path(__file__).with_name(script)), run_name="__main__")
