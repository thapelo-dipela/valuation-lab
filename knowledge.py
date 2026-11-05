"""Versioned source registry, searchable skills and immutable run/evidence storage."""

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent


@contextmanager
def database():
    path = Path(
        os.environ.get("VALUATION_DB", str(ROOT / "data" / "valuation.sqlite3"))
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript((ROOT / "data" / "schema.sql").read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "data" / "knowledge.json").read_text(encoding="utf-8"))
    with conn:
        for source in catalog["sources"]:
            conn.execute(
                "INSERT OR REPLACE INTO sources(id,payload) VALUES (?,?)",
                (source["id"], json.dumps(source)),
            )
        for skill in catalog["skills"]:
            conn.execute(
                "INSERT OR REPLACE INTO skills(id,domain,title,payload) VALUES (?,?,?,?)",
                (skill["id"], skill["domain"], skill["title"], json.dumps(skill)),
            )
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def search(query="", domain=""):
    with database() as conn:
        rows = conn.execute(
            "SELECT payload FROM skills WHERE (?='' OR domain=?) ORDER BY domain,title",
            (domain, domain),
        ).fetchall()
        sources = [
            json.loads(r[0])
            for r in conn.execute("SELECT payload FROM sources ORDER BY id")
        ]
    terms = re.findall(r"[\w-]+", query.lower())
    ranked = []
    for row in rows:
        item = json.loads(row[0])
        body = json.dumps(item).lower()
        score = sum(body.count(t) for t in terms)
        if not terms or all(t in body for t in terms):
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return dict(
        version="1.0.0",
        skills=[x[1] for x in ranked],
        sources=sources,
        scope="Original curated methods and source metadata, not a reproduction of CFA or CFP curricula. Lexical retrieval, not an embedded language model.",
    )


def skill_text(skill_id):
    with database() as conn:
        row = conn.execute(
            "SELECT payload FROM skills WHERE id=?", (skill_id,)
        ).fetchone()
    if not row:
        return None
    item = json.loads(row[0])
    # Domain comes from repository-controlled catalog, never a caller path.
    return (ROOT / "skills" / item["domain"] / "SKILL.md").read_text(encoding="utf-8")


def save_run(result, analysis, simulation=None):
    run_id = str(uuid4())
    catalog_hash = sha256((ROOT / "data" / "knowledge.json").read_bytes()).hexdigest()
    payload = json.dumps(
        dict(
            result=result,
            analysis=analysis,
            simulation=simulation,
            knowledge_catalog_sha256=catalog_hash,
        ),
        sort_keys=True,
        allow_nan=False,
    )
    with database() as conn:
        conn.execute(
            "INSERT INTO runs(id,created_at,input_hash,payload_hash,payload) VALUES (?,?,?,?,?)",
            (
                run_id,
                datetime.now(timezone.utc).isoformat(),
                result["input_sha256"],
                sha256(payload.encode()).hexdigest(),
                payload,
            ),
        )
    return run_id


def runs(run_id=None):
    with database() as conn:
        if run_id:
            row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            return dict(row) | {"payload": json.loads(row["payload"])} if row else None
        return [
            dict(r)
            for r in conn.execute(
                "SELECT id,created_at,input_hash,payload_hash FROM runs ORDER BY created_at DESC LIMIT 100"
            )
        ]


def record_evidence(run_id, evidence):
    with database() as conn:
        if not conn.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
            return None
        item = evidence.model_dump(mode="json")
        evidence_id = str(uuid4())
        conn.execute(
            "INSERT INTO evidence(id,run_id,payload) VALUES (?,?,?)",
            (evidence_id, run_id, json.dumps(item)),
        )
    return dict(id=evidence_id, run_id=run_id, **item)


def evidence_for(run_id):
    with database() as conn:
        return [
            dict(id=r[0], **json.loads(r[1]))
            for r in conn.execute(
                "SELECT id,payload FROM evidence WHERE run_id=?", (run_id,)
            )
        ]


def save_snapshot(provider, data):
    payload = json.dumps(data, sort_keys=True, allow_nan=False)
    fingerprint = sha256(payload.encode()).hexdigest()
    snapshot_id = str(uuid4())
    with database() as conn:
        conn.execute(
            "INSERT INTO data_snapshots VALUES (?,?,?,?,?)",
            (
                snapshot_id,
                datetime.now(timezone.utc).isoformat(),
                provider,
                fingerprint,
                payload,
            ),
        )
    return snapshot_id


def snapshot(snapshot_id):
    with database() as conn:
        row = conn.execute(
            "SELECT * FROM data_snapshots WHERE id=?", (snapshot_id,)
        ).fetchone()
    return dict(row) | {"payload": json.loads(row["payload"])} if row else None
