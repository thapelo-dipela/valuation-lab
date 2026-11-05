import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from api import app
import knowledge
from providers import select_company_fact, world_bank


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VALUATION_DB", str(tmp_path / "test.sqlite3"))
    with TestClient(app) as c:
        yield c


def test_case_history_and_evidence(client):
    case = client.get("/api/v1/example").json()
    r = client.post("/api/v1/analysis", json=dict(case=case, save=True))
    assert r.status_code == 200, r.text
    payload = r.json()
    run_id = payload["run_id"]
    saved = client.get("/api/v1/runs/" + run_id).json()
    assert saved["payload"]["result"] == payload["result"]
    assert saved["workflow"]["status"] == "research_required"
    e = dict(
        claim="Test growth evidence",
        input_path="drivers.revenue_growth",
        source_url="https://example.com/report",
        publisher="Test",
        published_date="2026-01-01",
        retrieved_date="2026-11-04",
        period="2025",
        units="percent",
        kind="reported",
        locator="page 1",
        review="corroborated",
        notes="Compared with independent filing",
    )
    assert client.post(f"/api/v1/runs/{run_id}/evidence", json=e).status_code == 201
    saved = client.get("/api/v1/runs/" + run_id).json()
    assert len(saved["evidence"]) == 1
    assert "drivers.revenue_growth" not in saved["workflow"]["missing_evidence"]
    with knowledge.database() as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE runs SET input_hash='changed' WHERE id=?", (run_id,))


def test_catalog_links_and_skills(client):
    data = client.get("/api/v1/knowledge").json()
    assert len(data["skills"]) == 35
    sources = {s["id"] for s in data["sources"]}
    assert len({s["domain"] for s in data["skills"]}) == 10
    for skill in data["skills"]:
        assert set(skill["source_ids"]) <= sources
        assert client.get("/api/v1/knowledge/" + skill["id"]).status_code == 200
    search = client.get(
        "/api/v1/knowledge", params={"q": "survival", "domain": "actuarial-risk"}
    ).json()
    assert search["skills"]
    assert all(s["domain"] == "actuarial-risk" for s in search["skills"])
    assert not client.get("/api/v1/knowledge", params={"q": "' OR 1=1 --"}).json()[
        "skills"
    ]


def test_api_validation_and_exports(client):
    case = client.get("/api/v1/example").json()
    bad = json.loads(json.dumps(case))
    bad["opening"]["equity"] = 0
    assert client.post("/api/v1/analysis", json={"case": bad}).status_code == 422
    assert client.get("/api/v1/runs/missing").status_code == 404
    assert client.get("/api/v1/knowledge/missing").status_code == 404
    for kind in ["docx", "xlsx", "pptx"]:
        r = client.post("/api/v1/export/" + kind, json=case)
        assert r.status_code == 200 and r.content[:2] == b"PK"
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_point_in_time_fact_selection():
    p = {
        "facts": {
            "us-gaap": {
                "Revenue": {
                    "units": {
                        "USD": [
                            dict(
                                start="2024-01-01",
                                end="2024-12-31",
                                filed="2025-02-01",
                                val=100,
                            ),
                            dict(
                                start="2024-01-01",
                                end="2024-12-31",
                                filed="2026-02-01",
                                val=110,
                            ),
                            dict(
                                start="2024-10-01",
                                end="2024-12-31",
                                filed="2025-02-01",
                                val=25,
                            ),
                        ]
                    }
                }
            }
        }
    }
    r = select_company_fact(p, "us-gaap", "Revenue", "USD", "2025-12-31")
    assert sorted(x["val"] for x in r["observations"]) == [25, 100]


def test_provider_mapping_preserves_missing(monkeypatch):
    monkeypatch.setattr(
        "providers.fetch_json",
        lambda url: dict(
            url=url,
            retrieved_at="test",
            sha256="test",
            data=[
                {"pages": 1},
                [{"date": "2024", "value": None, "countryiso3code": "ZAF"}],
            ],
        ),
    )
    r = world_bank()
    assert r["observations"][0]["value"] is None
    with pytest.raises(ValueError):
        world_bank(country="../bad")
