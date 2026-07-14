from __future__ import annotations

import csv
from io import StringIO

from fastapi.testclient import TestClient

from app.main import app
from app.renewal_kpis import KPI_IDS


client = TestClient(app)


def test_phase1_to_phase2_r01_navigation_api_flow() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})

    candidates = client.get("/api/candidates")
    assert candidates.status_code == 200
    r01 = next(record for record in candidates.json()["records"] if record["candidate_id"] == "R-01")
    assert r01["candidate_rank"] == 1

    detail = client.get(f"/api/v1/phase2/candidates/{r01['candidate_id']}")
    assert detail.status_code == 200
    assert detail.json()["candidate_id"] == "R-01"

    current = client.get("/api/renewal/R-01/current")
    assert current.status_code == 200
    payload = current.json()
    assert payload["buildings"]["features"]
    assert payload["roads"]["features"]
    assert payload["facilities"]["features"]


def test_phase2_end_to_end_scenario_comparison_summary_and_exports() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})

    scenarios = client.get("/api/renewal/R-01/scenarios")
    assert scenarios.status_code == 200
    assert [record["scenario_id"] for record in scenarios.json()["records"]] == ["0", "A", "B", "C"]

    run_a = client.post("/api/renewal/R-01/scenarios/A/run-kpis")
    assert run_a.status_code == 200
    assert run_a.json()["summary"]["scenario_id"] == "A"

    comparison = client.get("/api/renewal/R-01/comparison")
    assert comparison.status_code == 200
    comparison_payload = comparison.json()
    assert comparison_payload["count"] == 4
    assert set(comparison_payload["rankings"].keys()) == {
        "resilience",
        "housing",
        "parking",
        "green_open_space",
        "transport",
        "disaster",
    }
    for rows in comparison_payload["rankings"].values():
        assert [row["rank"] for row in rows] == [1, 2, 3, 4]
        assert all(row["kpi_ids"] for row in rows)

    for scenario_id in ["0", "A", "B", "C"]:
        kpis = client.get(f"/api/renewal/R-01/scenarios/{scenario_id}/kpis")
        summary = client.get(f"/api/renewal/R-01/scenarios/{scenario_id}/summary")
        assert kpis.status_code == 200
        assert summary.status_code == 200
        assert kpis.json()["count"] == len(KPI_IDS)
        assert summary.json()["data_disclaimer"]

    assert client.get("/api/renewal/R-01/export/scenarios/A.json").status_code == 200
    for layer in ["buildings", "roads", "facilities"]:
        exported = client.get(f"/api/renewal/R-01/export/scenarios/A/{layer}.geojson")
        assert exported.status_code == 200
        payload = exported.json()
        assert payload["type"] == "FeatureCollection"
        assert payload["metadata"]["scenario_id"] == "A"
        assert payload["features"]

    csv_response = client.get("/api/renewal/R-01/export/scenarios/A/kpis.csv")
    assert csv_response.status_code == 200
    rows = list(csv.DictReader(StringIO(csv_response.text)))
    assert len(rows) == len(KPI_IDS)
    assert rows[0]["scenario_id"] == "A"

    summary_export = client.get("/api/renewal/R-01/export/scenarios/A/decision-summary.json")
    assert summary_export.status_code == 200
    assert summary_export.json()["summary"]["scenario_id"] == "A"


def test_phase2_export_returns_404_for_unknown_layer_or_scenario() -> None:
    assert client.get("/api/renewal/R-01/export/scenarios/Z.json").status_code == 404
    assert client.get("/api/renewal/R-01/export/scenarios/A/blocks.geojson").status_code == 404
