"""Download and archive a SEC companyfacts snapshot; never auto-map balances.

python scripts/ingest_sec.py --cik 320193 --contact you@example.com
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import company_facts
from knowledge import save_snapshot

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cik", required=True)
    parser.add_argument(
        "--contact", required=True, help="Your contact email for the SEC User-Agent"
    )
    args = parser.parse_args()
    data = company_facts(args.cik, args.contact)
    print("Saved SEC companyfacts snapshot:", save_snapshot("SEC EDGAR", data))
    print("Source SHA-256:", data["sha256"])
    print(
        "Analyst-approved taxonomy, unit and period selection is required before using observations."
    )
