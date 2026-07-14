from fastapi.testclient import TestClient

from app.main import app


def test_phase_one_end_to_end_simulation_scoring_candidates_and_exports() -> None:
    client = TestClient(app)
    request_payload = {
        "random_seed": 2026,
        "old_area_intensity": 75,
        "population_density": 70,
        "public_transport_level": 45,
        "green_space_level": 35,
        "disaster_risk_level": 80,
    }

    generate_response = client.post("/api/simulation/generate", json=request_payload)
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert generated["status"] == "generated"
    assert generated["parameters"] == request_payload

    simulation_response = client.get("/api/simulation/data")
    assert simulation_response.status_code == 200
    simulation_payload = simulation_response.json()
    assert simulation_payload["parameters"] == request_payload
    assert simulation_payload["count"] == generated["grid_count"]

    resilience_response = client.get("/api/resilience")
    assert resilience_response.status_code == 200
    resilience_payload = resilience_response.json()
    assert resilience_payload["count"] == generated["grid_count"]
    assert "resilience_score" in resilience_payload["records"][0]

    candidates_response = client.get("/api/candidates")
    assert candidates_response.status_code == 200
    candidates_payload = candidates_response.json()
    assert candidates_payload["count"] == len(candidates_payload["records"])
    for candidate in candidates_payload["records"]:
        assert candidate["candidate_id"].startswith("R-")
        assert candidate["grid_count"] >= 2

    grid_export_response = client.get("/api/export/grids.geojson")
    assert grid_export_response.status_code == 200
    grid_export = grid_export_response.json()
    assert grid_export["type"] == "FeatureCollection"
    assert len(grid_export["features"]) == generated["grid_count"]
    assert "resilience_score" in grid_export["features"][0]["properties"]

    csv_response = client.get("/api/export/indicators.csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    csv_text = csv_response.text
    assert "grid_id" in csv_text.splitlines()[0]
    assert "renewal_potential" in csv_text.splitlines()[0]

    candidate_export_response = client.get("/api/export/candidates.geojson")
    assert candidate_export_response.status_code == 200
    candidate_export = candidate_export_response.json()
    assert candidate_export["type"] == "FeatureCollection"
    assert len(candidate_export["features"]) == candidates_payload["count"]
