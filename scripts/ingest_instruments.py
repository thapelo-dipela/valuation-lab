"""Import the pinned full FinanceDatabase equities universe into local SQLite."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from instruments import import_financedatabase
from knowledge import save_snapshot

if __name__ == "__main__":
    result = import_financedatabase()
    result["snapshot_id"] = save_snapshot("FinanceDatabase import manifest", result)
    print(json.dumps(result, indent=2))
