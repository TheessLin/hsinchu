from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_phase2_r01_detail_api_returns_candidate_handoff_data() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/v1/phase2/candidates/R-01")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "R-01"
    assert payload["source_candidate_rank"] == 1
    assert payload["grid_count"] == len(payload["grid_ids"])
    assert payload["grid_count"] >= 2
    assert payload["area"] > 0
    assert 0 <= payload["average_resilience_score"] <= 100
    assert 0 <= payload["average_renewal_opportunity_score"] <= 100
    assert len(payload["primary_issues"]) > 0
    assert payload["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert payload["seed"] == 42
    assert payload["simulation_parameters"]["random_seed"] == 42
    assert payload["data_type"] == "synthetic"
    assert "official policy" in payload["disclaimer"]


def test_phase2_candidate_detail_api_returns_404_for_unknown_candidate() -> None:
    response = client.get("/api/v1/phase2/candidates/R-999")

    assert response.status_code == 404
