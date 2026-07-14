from fastapi.testclient import TestClient

from app.grids import generate_analysis_grids
from app.main import app
from app.simulation import FIELD_RANGES, SYNTHETIC_FIELDS, generate_synthetic_data


def test_synthetic_data_contains_required_fields() -> None:
    data = generate_synthetic_data(seed=42)

    expected_fields = {
        "grid_id",
        "centroid_x",
        "centroid_y",
        "district_type",
        "land_use_type",
        *SYNTHETIC_FIELDS,
    }
    assert expected_fields <= set(data.columns)
    assert len(data) == len(generate_analysis_grids())
    assert data["grid_id"].is_unique


def test_synthetic_data_field_ranges_are_bounded() -> None:
    data = generate_synthetic_data(seed=42)

    for field, (lower, upper) in FIELD_RANGES.items():
        assert data[field].between(lower, upper).all(), field


def test_synthetic_data_is_reproducible_with_fixed_seed() -> None:
    first = generate_synthetic_data(seed=2026)
    second = generate_synthetic_data(seed=2026)

    assert first.to_dict(orient="records") == second.to_dict(orient="records")


def test_synthetic_data_changes_with_different_seed() -> None:
    first = generate_synthetic_data(seed=42)
    second = generate_synthetic_data(seed=43)

    assert first[SYNTHETIC_FIELDS].to_dict(orient="records") != second[SYNTHETIC_FIELDS].to_dict(orient="records")


def test_scenario_parameters_change_rule_based_baselines() -> None:
    low_pressure = generate_synthetic_data(
        seed=42,
        old_area_intensity=20,
        population_density=20,
        public_transport_level=20,
        green_space_level=20,
        disaster_risk_level=20,
    )
    high_pressure = generate_synthetic_data(
        seed=42,
        old_area_intensity=80,
        population_density=80,
        public_transport_level=80,
        green_space_level=80,
        disaster_risk_level=80,
    )

    assert high_pressure["average_building_age"].mean() > low_pressure["average_building_age"].mean()
    assert high_pressure["population"].mean() > low_pressure["population"].mean()
    assert high_pressure["bus_access_score"].mean() > low_pressure["bus_access_score"].mean()
    assert high_pressure["green_ratio"].mean() > low_pressure["green_ratio"].mean()
    assert high_pressure["fire_risk"].mean() > low_pressure["fire_risk"].mean()


def test_rule_based_patterns_match_urban_assumptions() -> None:
    data = generate_synthetic_data(seed=42)
    core = data[data["commercial_activity"] >= data["commercial_activity"].quantile(0.75)]
    edge = data[data["bus_access_score"] <= data["bus_access_score"].quantile(0.25)]

    assert core["population"].mean() > edge["population"].mean()
    assert core["building_count"].mean() > edge["building_count"].mean()
    assert core["average_building_age"].mean() > edge["average_building_age"].mean()
    assert core["green_ratio"].mean() < edge["green_ratio"].mean()
    assert edge["medical_access_score"].mean() < core["medical_access_score"].mean()


def test_generate_simulation_api_stores_seeded_data() -> None:
    client = TestClient(app)

    generate_response = client.post("/api/simulation/generate", json={"seed": 77})

    assert generate_response.status_code == 200
    generate_payload = generate_response.json()
    assert generate_payload["status"] == "generated"
    assert generate_payload["seed"] == 77
    assert generate_payload["parameters"]["random_seed"] == 77
    assert generate_payload["grid_count"] == len(generate_analysis_grids())

    data_response = client.get("/api/simulation/data")
    assert data_response.status_code == 200
    data_payload = data_response.json()
    assert data_payload["seed"] == 77
    assert data_payload["parameters"]["random_seed"] == 77
    assert data_payload["count"] == generate_payload["grid_count"]
    assert len(data_payload["records"]) == generate_payload["grid_count"]


def test_get_simulation_grid_api_returns_one_record() -> None:
    client = TestClient(app)
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/simulation/grid/HC-GRID-0001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["grid_id"] == "HC-GRID-0001"
    assert set(SYNTHETIC_FIELDS) <= set(payload)


def test_get_simulation_grid_api_returns_404_for_unknown_grid() -> None:
    client = TestClient(app)

    response = client.get("/api/simulation/grid/HC-GRID-9999")

    assert response.status_code == 404
