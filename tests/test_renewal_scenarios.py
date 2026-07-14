from __future__ import annotations

from fastapi.testclient import TestClient
from shapely.geometry import shape

from app.main import app
from app.renewal_scenarios import ScenarioParameterValues, get_scenario_run_records
from app.simulation import generate_and_store_simulation


client = TestClient(app)


def test_r01_scenarios_api_returns_four_parameterized_scenarios() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/renewal/R-01/scenarios")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "R-01"
    assert payload["count"] == 4
    assert [record["scenario_id"] for record in payload["records"]] == ["0", "A", "B", "C"]
    assert "properties" in payload["parameter_schema"]
    for record in payload["records"]:
        _assert_scenario_contract(record)


def test_r01_current_scenario_preserves_current_condition() -> None:
    generate_and_store_simulation(seed=42)

    response = client.get("/api/renewal/R-01/scenarios/0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_name"] == "Current"
    assert payload["removed_building_ids"] == []
    assert payload["added_buildings"] == []
    assert payload["modified_roads"] == []
    assert payload["added_facilities"] == []


def test_r01_housing_scenario_adds_midrise_housing_and_parking() -> None:
    generate_and_store_simulation(seed=42)

    response = client.get("/api/renewal/R-01/scenarios/A")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_name"] == "Housing"
    assert 3 <= len(payload["added_buildings"]) <= 5
    assert len(payload["removed_building_ids"]) > 0
    assert all(building["use_type"] == "residential" for building in payload["added_buildings"])
    assert sum(building["residential_units"] for building in payload["added_buildings"]) > 0
    assert sum(building["parking_spaces"] for building in payload["added_buildings"]) > 0
    assert any(facility["facility_type"] == "open_space" for facility in payload["added_facilities"])


def test_r01_resilience_scenario_adds_facilities_and_widens_roads() -> None:
    generate_and_store_simulation(seed=42)

    response = client.get("/api/renewal/R-01/scenarios/B")

    assert response.status_code == 200
    payload = response.json()
    facility_types = {facility["facility_type"] for facility in payload["added_facilities"]}
    assert len(payload["added_buildings"]) < 3
    assert {"park", "disaster_plaza", "elderly_service", "childcare"}.issubset(facility_types)
    assert len(payload["modified_roads"]) > 0
    assert all(road["emergency_accessible"] for road in payload["modified_roads"])


def test_r01_transit_commercial_scenario_increases_mixed_use_and_access() -> None:
    generate_and_store_simulation(seed=42)

    response = client.get("/api/renewal/R-01/scenarios/C")

    assert response.status_code == 200
    payload = response.json()
    facility_types = {facility["facility_type"] for facility in payload["added_facilities"]}
    assert all(building["use_type"] == "mixed_use" for building in payload["added_buildings"])
    assert sum(building["commercial_floor_area"] for building in payload["added_buildings"]) > 0
    assert sum(building["daytime_population"] for building in payload["added_buildings"]) > 0
    assert {"bus_stop", "bike_station", "shared_parking"}.issubset(facility_types)
    assert len(payload["modified_roads"]) > 0


def test_r01_scenario_run_is_reproducible_for_same_input() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})
    request = {
        "parameter_values": {
            "removal_count": 6,
            "housing_building_count": 3,
            "housing_floors": 11,
            "underground_parking_per_building": 90,
        }
    }

    first = client.post("/api/renewal/R-01/scenarios/A/run", json=request)
    second = client.post("/api/renewal/R-01/scenarios/A/run", json=request)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_r01_scenario_run_records_are_preserved() -> None:
    before = len(get_scenario_run_records())

    response = client.post("/api/renewal/R-01/scenarios/B/run", json={"parameter_values": {"emergency_route_count": 2}})

    assert response.status_code == 200
    records = get_scenario_run_records()
    assert len(records) == before + 1
    assert records[-1] == response.json()


def test_r01_scenario_request_uses_json_schema_validation() -> None:
    schema = ScenarioParameterValues.model_json_schema()
    assert schema["properties"]["housing_building_count"]["maximum"] == 5

    response = client.post(
        "/api/renewal/R-01/scenarios/A/run",
        json={"parameter_values": {"housing_building_count": 9}},
    )

    assert response.status_code == 422


def test_r01_scenario_returns_404_for_unknown_scenario() -> None:
    response = client.get("/api/renewal/R-01/scenarios/Z")

    assert response.status_code == 404


def test_r01_scenario_geometries_are_valid_geojson() -> None:
    generate_and_store_simulation(seed=42)

    payload = client.get("/api/renewal/R-01/scenarios/B").json()

    for collection_name in ["added_buildings", "modified_roads", "added_facilities"]:
        for item in payload[collection_name]:
            geometry = shape(item["geometry"])
            assert geometry.is_valid
            assert not geometry.is_empty


def _assert_scenario_contract(record: dict[str, object]) -> None:
    for field in [
        "scenario_id",
        "scenario_name",
        "description",
        "assumptions",
        "removed_building_ids",
        "added_buildings",
        "modified_roads",
        "added_facilities",
        "parameter_values",
        "created_at",
        "simulation_seed",
    ]:
        assert field in record
