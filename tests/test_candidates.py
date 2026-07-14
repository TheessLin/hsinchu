import geopandas as gpd
from fastapi.testclient import TestClient
from shapely.geometry import box

from app.candidates import build_candidate_areas, get_candidate_areas
from app.grids import GRID_CRS
from app.main import app
from app.simulation import generate_and_store_simulation


def test_candidate_builder_clusters_adjacent_low_score_grids_and_excludes_singletons() -> None:
    grids = gpd.GeoDataFrame(
        [
            {"grid_id": "A", "geometry": box(0, 0, 500, 500)},
            {"grid_id": "B", "geometry": box(500, 0, 1000, 500)},
            {"grid_id": "C", "geometry": box(2000, 0, 2500, 500)},
            {"grid_id": "D", "geometry": box(1000, 500, 1500, 1000)},
            {"grid_id": "E", "geometry": box(1000, 0, 1500, 500)},
        ],
        geometry="geometry",
        crs=GRID_CRS,
    )
    records = [
        _candidate_record("A", resilience_score=41, renewal_potential=70),
        _candidate_record("B", resilience_score=39, renewal_potential=68),
        _candidate_record("C", resilience_score=38, renewal_potential=90),
        _candidate_record("D", resilience_score=35, renewal_potential=85),
        _candidate_record("E", resilience_score=52, renewal_potential=95),
    ]

    candidates = build_candidate_areas(records, grids)

    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == "R-01"
    assert candidates[0]["candidate_rank"] == 1
    assert candidates[0]["grid_count"] == 2
    assert candidates[0]["grid_ids"] == ["A", "B"]
    assert candidates[0]["area"] == 500000
    assert candidates[0]["average_resilience_score"] == 40
    assert candidates[0]["average_renewal_opportunity_score"] == 69
    assert len(candidates[0]["primary_issues"]) == 3
    assert candidates[0]["geometry"]["type"] in {"Polygon", "MultiPolygon"}


def test_generated_candidates_match_screening_rules() -> None:
    generate_and_store_simulation(seed=42)

    candidates = get_candidate_areas()

    assert len(candidates) > 0
    assert [candidate["candidate_rank"] for candidate in candidates] == list(range(1, len(candidates) + 1))
    assert candidates[0]["candidate_id"] == "R-01"
    for candidate in candidates:
        assert candidate["grid_count"] >= 2
        assert candidate["average_resilience_score"] < 45
        assert candidate["average_renewal_opportunity_score"] >= 60
        assert candidate["candidate_id"].startswith("R-")
        assert candidate["primary_issues"]


def test_candidates_api_returns_ranked_candidate_areas() -> None:
    client = TestClient(app)
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/candidates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(payload["records"])
    assert payload["count"] > 0
    first_candidate = payload["records"][0]
    assert first_candidate["candidate_id"] == "R-01"
    assert first_candidate["candidate_rank"] == 1
    assert first_candidate["grid_count"] >= 2
    assert "geometry" in first_candidate


def test_candidate_detail_api_returns_404_for_unknown_candidate() -> None:
    client = TestClient(app)

    response = client.get("/api/candidates/R-999")

    assert response.status_code == 404


def test_candidate_detail_api_returns_one_candidate() -> None:
    client = TestClient(app)
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/candidates/R-01")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "R-01"
    assert payload["candidate_rank"] == 1
    assert payload["grid_count"] >= 2


def _candidate_record(grid_id: str, resilience_score: float, renewal_potential: float) -> dict[str, object]:
    return {
        "grid_id": grid_id,
        "resilience_score": resilience_score,
        "renewal_potential": renewal_potential,
        "built_environment_score": 35,
        "disaster_evacuation_score": 40,
        "transport_access_score": 45,
        "social_demographic_score": 50,
        "living_health_score": 55,
        "renewal_potential_score": 30,
    }
