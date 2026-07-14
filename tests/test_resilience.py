import pytest
from fastapi.testclient import TestClient

from app.grids import generate_analysis_grids
from app.main import app
from app.resilience import DIMENSION_WEIGHTS, calculate_resilience_record, get_resilience_records
from app.simulation import generate_and_store_simulation


DIMENSION_SCORE_FIELDS = list(DIMENSION_WEIGHTS)


def test_best_case_extreme_values_score_high() -> None:
    result = calculate_resilience_record(_best_case_record())

    for field in DIMENSION_SCORE_FIELDS:
        assert result[field] == 100
    assert result["resilience_score"] == 100
    assert result["renewal_potential"] == 0
    assert result["score_details"]["renewal_potential_score"]["raw_renewal_potential"] == 0


def test_worst_case_extreme_values_score_low() -> None:
    result = calculate_resilience_record(_worst_case_record())

    for field in DIMENSION_SCORE_FIELDS:
        assert result[field] == 0
    assert result["resilience_score"] == 0
    assert result["renewal_potential"] == 100
    assert result["score_details"]["renewal_potential_score"]["raw_renewal_potential"] == 100


def test_boundary_values_stay_within_score_range() -> None:
    records = [_best_case_record(), _worst_case_record(), _mid_case_record()]

    for record in records:
        result = calculate_resilience_record(record)
        for field in [*DIMENSION_SCORE_FIELDS, "resilience_score"]:
            assert 0 <= result[field] <= 100


def test_weighted_resilience_score_matches_formula() -> None:
    result = calculate_resilience_record(_mid_case_record())
    expected = round(sum(result[field] * weight for field, weight in DIMENSION_WEIGHTS.items()), 2)

    assert result["resilience_score"] == pytest.approx(expected)


def test_each_dimension_outputs_calculation_details() -> None:
    result = calculate_resilience_record(_mid_case_record())

    assert set(result["score_details"]) == set(DIMENSION_SCORE_FIELDS)
    for field in DIMENSION_SCORE_FIELDS:
        detail = result["score_details"][field]
        assert "score" in detail
        assert "components" in detail
        assert "weights" in detail
        assert detail["components"]
        assert detail["weights"]


def test_renewal_potential_score_is_inverse_of_raw_pressure() -> None:
    low_pressure = calculate_resilience_record({**_mid_case_record(), "renewal_potential": 10})
    high_pressure = calculate_resilience_record({**_mid_case_record(), "renewal_potential": 90})

    assert low_pressure["renewal_potential"] == 10
    assert high_pressure["renewal_potential"] == 90
    assert low_pressure["renewal_potential_score"] > high_pressure["renewal_potential_score"]


def test_generated_resilience_records_are_bounded() -> None:
    generate_and_store_simulation(seed=42)
    records = get_resilience_records()

    assert len(records) == len(generate_analysis_grids())
    for record in records:
        for field in [*DIMENSION_SCORE_FIELDS, "resilience_score"]:
            assert 0 <= record[field] <= 100


def test_resilience_api_returns_records() -> None:
    client = TestClient(app)
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/resilience")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(generate_analysis_grids())
    assert len(payload["records"]) == payload["count"]
    assert set(DIMENSION_SCORE_FIELDS) <= set(payload["records"][0])
    assert "score_details" in payload["records"][0]


def test_resilience_grid_api_returns_one_record() -> None:
    client = TestClient(app)
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/resilience/HC-GRID-0001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["grid_id"] == "HC-GRID-0001"
    assert set(DIMENSION_SCORE_FIELDS) <= set(payload)
    assert "score_details" in payload


def test_resilience_grid_api_returns_404_for_unknown_grid() -> None:
    client = TestClient(app)

    response = client.get("/api/resilience/HC-GRID-9999")

    assert response.status_code == 404


def _base_record() -> dict[str, object]:
    return {
        "grid_id": "TEST-GRID",
        "centroid_x": 120.95,
        "centroid_y": 24.8,
        "district_type": "東區",
        "land_use_type": "住宅與科技服務混合",
    }


def _best_case_record() -> dict[str, object]:
    return {
        **_base_record(),
        "population": 30,
        "daytime_population": 20,
        "elderly_ratio": 0.06,
        "child_ratio": 0.14,
        "building_count": 1,
        "average_building_age": 3,
        "old_building_ratio": 0.02,
        "building_coverage_ratio": 0.08,
        "narrow_road_ratio": 0.05,
        "open_space_ratio": 0.65,
        "green_ratio": 0.55,
        "parking_supply": 900,
        "parking_demand": 0,
        "bus_access_score": 100,
        "bike_access_score": 100,
        "walkability_score": 100,
        "shelter_access_score": 100,
        "fire_risk": 0,
        "flood_risk": 0,
        "medical_access_score": 100,
        "park_access_score": 100,
        "commercial_activity": 100,
        "ownership_complexity": 0,
        "renewal_potential": 0,
    }


def _worst_case_record() -> dict[str, object]:
    return {
        **_base_record(),
        "population": 2400,
        "daytime_population": 3200,
        "elderly_ratio": 0.32,
        "child_ratio": 0.05,
        "building_count": 120,
        "average_building_age": 60,
        "old_building_ratio": 0.85,
        "building_coverage_ratio": 0.82,
        "narrow_road_ratio": 0.75,
        "open_space_ratio": 0.03,
        "green_ratio": 0.02,
        "parking_supply": 0,
        "parking_demand": 1400,
        "bus_access_score": 0,
        "bike_access_score": 0,
        "walkability_score": 0,
        "shelter_access_score": 0,
        "fire_risk": 100,
        "flood_risk": 100,
        "medical_access_score": 0,
        "park_access_score": 0,
        "commercial_activity": 0,
        "ownership_complexity": 100,
        "renewal_potential": 100,
    }


def _mid_case_record() -> dict[str, object]:
    return {
        **_base_record(),
        "population": 1200,
        "daytime_population": 1500,
        "elderly_ratio": 0.18,
        "child_ratio": 0.14,
        "building_count": 60,
        "average_building_age": 30,
        "old_building_ratio": 0.4,
        "building_coverage_ratio": 0.45,
        "narrow_road_ratio": 0.35,
        "open_space_ratio": 0.3,
        "green_ratio": 0.28,
        "parking_supply": 400,
        "parking_demand": 800,
        "bus_access_score": 60,
        "bike_access_score": 55,
        "walkability_score": 58,
        "shelter_access_score": 62,
        "fire_risk": 45,
        "flood_risk": 35,
        "medical_access_score": 70,
        "park_access_score": 50,
        "commercial_activity": 65,
        "ownership_complexity": 50,
        "renewal_potential": 55,
    }
