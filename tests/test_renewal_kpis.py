from __future__ import annotations

import geopandas as gpd
from fastapi.testclient import TestClient

from app.grids import GRID_CRS
from app.main import app
from app.renewal_current import RenewalCurrentData
from app.renewal_kpis import (
    AppliedScenarioData,
    KPI_IDS,
    calculate_emergency_access_score,
    calculate_green_ratio,
    calculate_percentage_change,
)
from app.simulation import generate_and_store_simulation


client = TestClient(app)


REQUIRED_KPI_FIELDS = {
    "kpi_id",
    "name",
    "value",
    "unit",
    "baseline_value",
    "absolute_change",
    "percentage_change",
    "formula_reference",
    "confidence_level",
    "assumptions",
}


def test_r01_scenario_kpis_api_returns_all_required_kpis() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/renewal/R-01/scenarios/B/kpis")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "R-01"
    assert payload["scenario_id"] == "B"
    assert payload["baseline_scenario_id"] == "0"
    assert payload["count"] == len(KPI_IDS)
    assert list(payload["kpis"].keys()) == KPI_IDS
    for record in payload["records"]:
        assert REQUIRED_KPI_FIELDS.issubset(record)


def test_r01_current_scenario_kpis_match_baseline() -> None:
    generate_and_store_simulation(seed=42)

    payload = client.get("/api/renewal/R-01/scenarios/0/kpis").json()

    for record in payload["records"]:
        assert record["value"] == record["baseline_value"]
        assert record["absolute_change"] == 0
        if record["baseline_value"] != 0:
            assert record["percentage_change"] == 0


def test_r01_housing_scenario_increases_units_and_parking_supply() -> None:
    generate_and_store_simulation(seed=42)

    payload = client.get("/api/renewal/R-01/scenarios/A/kpis").json()
    kpis = payload["kpis"]

    assert kpis["residential_units"]["value"] > kpis["residential_units"]["baseline_value"]
    assert kpis["parking_supply"]["value"] > kpis["parking_supply"]["baseline_value"]


def test_r01_resilience_scenario_improves_green_and_emergency_access() -> None:
    generate_and_store_simulation(seed=42)

    payload = client.get("/api/renewal/R-01/scenarios/B/kpis").json()
    kpis = payload["kpis"]

    assert kpis["park_area_m2"]["value"] > kpis["park_area_m2"]["baseline_value"]
    assert kpis["green_ratio"]["value"] > kpis["green_ratio"]["baseline_value"]
    assert kpis["emergency_access_score"]["value"] > kpis["emergency_access_score"]["baseline_value"]


def test_r01_transit_commercial_scenario_improves_activity_and_access() -> None:
    generate_and_store_simulation(seed=42)

    payload = client.get("/api/renewal/R-01/scenarios/C/kpis").json()
    kpis = payload["kpis"]

    assert kpis["daytime_population"]["value"] > kpis["daytime_population"]["baseline_value"]
    assert kpis["commercial_activity_score"]["value"] > kpis["commercial_activity_score"]["baseline_value"]
    assert kpis["bus_access_score"]["value"] >= kpis["bus_access_score"]["baseline_value"]
    assert kpis["bike_access_score"]["value"] >= kpis["bike_access_score"]["baseline_value"]


def test_r01_comparison_api_returns_all_scenarios() -> None:
    generate_and_store_simulation(seed=42)

    response = client.get("/api/renewal/R-01/comparison")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "R-01"
    assert payload["baseline_scenario_id"] == "0"
    assert [scenario["scenario_id"] for scenario in payload["scenarios"]] == ["0", "A", "B", "C"]
    assert all(len(scenario["records"]) == len(KPI_IDS) for scenario in payload["scenarios"])


def test_r01_scenario_kpis_returns_404_for_unknown_scenario() -> None:
    response = client.get("/api/renewal/R-01/scenarios/Z/kpis")

    assert response.status_code == 404


def test_percentage_change_does_not_divide_by_zero() -> None:
    result = calculate_percentage_change(value=10, baseline_value=0)

    assert result.value is None
    assert result.reason is not None
    assert "zero" in result.reason


def test_extreme_empty_inputs_return_null_with_reason() -> None:
    data = _empty_applied_scenario_data()

    green = calculate_green_ratio(data, {})
    emergency = calculate_emergency_access_score(data, {})

    assert green.value is None
    assert green.reason is not None
    assert emergency.value is None
    assert emergency.reason is not None


def _empty_applied_scenario_data() -> AppliedScenarioData:
    blocks = gpd.GeoDataFrame({"area_m2": [], "open_space_ratio": []}, geometry=[], crs=GRID_CRS)
    buildings = gpd.GeoDataFrame(
        {
            "building_id": [],
            "residential_units": [],
            "estimated_population": [],
            "commercial_floor_area": [],
            "parking_spaces": [],
            "use_type": [],
            "age": [],
        },
        geometry=[],
        crs=GRID_CRS,
    )
    roads = gpd.GeoDataFrame(
        {"road_id": [], "width_m": [], "sidewalk_width_m": [], "emergency_accessible": [], "pedestrian_capacity": []},
        geometry=[],
        crs=GRID_CRS,
    )
    facilities = gpd.GeoDataFrame({"facility_id": [], "facility_type": [], "capacity": [], "service_radius_m": []}, geometry=[], crs=GRID_CRS)
    current = RenewalCurrentData(seed=42, blocks=blocks, buildings=buildings, roads=roads, facilities=facilities)
    return AppliedScenarioData(
        scenario={"scenario_id": "0", "removed_building_ids": [], "added_facilities": [], "parameter_values": {}},
        current=current,
        buildings=buildings,
        roads=roads,
        facilities=facilities,
        land_area_m2=0,
    )
