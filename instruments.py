"""FinanceDatabase security-master adapter; symbols are discovery, not fundamentals."""

import bz2
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import httpx
from knowledge import database, ROOT

PIN = "35523e03ee411abe673e093aed09b2769c7a442c"
URL = f"https://raw.githubusercontent.com/JerBouma/FinanceDatabase/{PIN}/compression/equities.bz2"


def ingest_rows(rows, commit=PIN):
    count = 0
    with database() as db:
        for row in rows:
            if count >= 500_000:
                raise ValueError("Security master exceeds 500,000 rows")
            if not row.get("symbol") or not row.get("name"):
                raise ValueError("Every instrument requires a symbol and name")
            delisted = str(row.get("delisted", "")).lower() in {"true", "1"}
            db.execute(
                "INSERT OR REPLACE INTO instruments VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    row["symbol"],
                    row.get("exchange", ""),
                    row["name"],
                    row.get("country", ""),
                    row.get("sector", ""),
                    row.get("industry", ""),
                    row.get("currency", ""),
                    int(delisted),
                    commit,
                    json.dumps(row),
                ),
            )
            count += 1
    return count


def import_financedatabase():
    chunks = []
    size = 0
    with httpx.stream("GET", URL, timeout=60, follow_redirects=False) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > 30_000_000:
                raise ValueError("Compressed database exceeds 30 MB")
            chunks.append(chunk)
    raw = b"".join(chunks)
    with bz2.BZ2File(io.BytesIO(raw)) as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8-sig", newline="") as text:
            count = ingest_rows(csv.DictReader(text))
    return dict(
        rows=count,
        source=URL,
        source_commit=PIN,
        sha256=sha256(raw).hexdigest(),
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        warning="Current constituent snapshot. No historical membership, live prices or financial statements. ZAC denotes cents; do not relabel as ZAR.",
    )


def search_instruments(
    query="", country="", sector="", exchange="", include_delisted=False, limit=50
):
    with database() as db:
        rows = db.execute(
            """SELECT payload FROM instruments WHERE source_commit=?
         AND (?='' OR country=?) AND (?='' OR sector=?) AND (?='' OR exchange=?)
         AND (? OR delisted=0) AND (?='' OR instr(lower(symbol||' '||name),lower(?))>0)
         ORDER BY symbol,exchange LIMIT ?""",
            (
                PIN,
                country,
                country,
                sector,
                sector,
                exchange,
                exchange,
                include_delisted,
                query,
                query,
                min(max(limit, 1), 100),
            ),
        ).fetchall()
        count = db.execute(
            "SELECT count(*) FROM instruments WHERE source_commit=?", (PIN,)
        ).fetchone()[0]
    return dict(
        source_commit=PIN,
        total_loaded=count,
        results=[json.loads(r[0]) for r in rows],
        status="ready" if count else "not_imported",
        scope="Security discovery only; company domicile is not listing market; duplicates across listings are retained.",
    )


def repository_catalog():
    return json.loads(
        (ROOT / "data/repository_catalog.json").read_text(encoding="utf-8")
    )
