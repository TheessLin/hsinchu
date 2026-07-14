from __future__ import annotations

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import shape

from app.grids import BASE_CRS, GRID_CRS
from app.main import app
from app.renewal_current import generate_r01_current_data
from app.simulation import generate_and_store_simulation


client = TestClient(app)


REQUIRED_FACILITY_TYPES = {
    "park",
    "shelter",
    "parking",
    "bus_stop",
    "bike_station",
    "clinic",
    "childcare",
    "elderly_service",
    "market",
}


def test_r01_current_api_returns_all_layers() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get("/api/renewal/R-01/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "R-01"
    assert payload["seed"] == 42
    assert payload["data_type"] == "synthetic"
    for layer in ["blocks", "buildings", "roads", "facilities"]:
        assert payload[layer]["type"] == "FeatureCollection"
        assert payload[layer]["metadata"]["layer"] == layer
        assert len(payload[layer]["features"]) > 0


@pytest.mark.parametrize(
    ("path", "required_field"),
    [
        ("/api/renewal/R-01/blocks", "block_id"),
        ("/api/renewal/R-01/buildings", "building_id"),
        ("/api/renewal/R-01/roads", "road_id"),
        ("/api/renewal/R-01/facilities", "facility_id"),
    ],
)
def test_r01_current_layer_apis_return_feature_collections(path: str, required_field: str) -> None:
    client.post("/api/simulation/generate", json={"seed": 42})

    response = client.get(path)

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert required_field in payload["features"][0]["properties"]


def test_r01_current_generator_is_reproducible() -> None:
    generate_and_store_simulation(seed=42)

    first = client.get("/api/renewal/R-01/current").json()
    second = client.get("/api/renewal/R-01/current").json()

    assert first == second


def test_r01_building_counts_and_field_ranges_are_valid() -> None:
    current = generate_r01_current_data(seed=42)

    assert 50 <= len(current.buildings) <= 150
    assert current.buildings["floors"].between(1, 14).all()
    assert current.buildings["height_m"].between(3.2, 44.8).all()
    assert current.buildings["construction_year"].between(1961, 2023).all()
    assert current.buildings["age"].between(3, 65).all()
    assert (current.buildings["residential_units"] >= 0).all()
    assert (current.buildings["commercial_floor_area"] >= 0).all()
    assert (current.buildings["estimated_population"] >= 0).all()
    assert (current.buildings["parking_spaces"] >= 0).all()
    assert set(current.buildings["renewal_status"]).issubset({"priority", "monitor", "stable"})


def test_r01_block_road_and_facility_field_ranges_are_valid() -> None:
    current = generate_r01_current_data(seed=42)

    assert current.blocks["building_coverage_ratio"].between(0.25, 0.78).all()
    assert current.blocks["floor_area_ratio"].between(0.6, 3.8).all()
    assert current.blocks["open_space_ratio"].between(0.08, 0.5).all()
    assert current.roads["width_m"].between(3.5, 14.5).all()
    assert current.roads["sidewalk_width_m"].between(0.2, 3.2).all()
    assert (current.roads["pedestrian_capacity"] > 0).all()
    assert set(current.facilities["facility_type"]) == REQUIRED_FACILITY_TYPES
    assert (current.facilities["capacity"] > 0).all()
    assert (current.facilities["service_radius_m"] > 0).all()


def test_r01_geometries_are_valid_and_buildings_stay_inside_blocks() -> None:
    current = generate_r01_current_data(seed=42)

    for layer in [current.blocks, current.buildings, current.roads, current.facilities]:
        assert layer.geometry.is_valid.all()
        assert not layer.geometry.is_empty.any()

    blocks_by_id = dict(zip(current.blocks["block_id"], current.blocks.geometry, strict=True))
    for _, building in current.buildings.iterrows():
        block = blocks_by_id[building["block_id"]]
        assert block.buffer(0.01).contains(building.geometry)


def test_r01_buildings_do_not_severely_overlap() -> None:
    current = generate_r01_current_data(seed=42)

    for _block_id, buildings in current.buildings.groupby("block_id"):
        geometries = list(buildings.geometry)
        for left_index, left_geometry in enumerate(geometries):
            for right_geometry in geometries[left_index + 1 :]:
                overlap_area = left_geometry.intersection(right_geometry).area
                if overlap_area == 0:
                    continue
                smaller_area = min(left_geometry.area, right_geometry.area)
                assert overlap_area / smaller_area <= 0.05


def test_r01_old_buildings_and_narrow_roads_are_spatially_related() -> None:
    current = generate_r01_current_data(seed=42)
    narrow_roads = current.roads[current.roads["width_m"] < 6.0]
    assert len(narrow_roads) > 0

    priority_buildings = current.buildings[current.buildings["renewal_status"] == "priority"]
    stable_buildings = current.buildings[current.buildings["renewal_status"] == "stable"]
    assert len(priority_buildings) > 0
    assert len(stable_buildings) > 0

    narrow_union = narrow_roads.geometry.union_all()
    priority_distance = priority_buildings.geometry.centroid.distance(narrow_union).mean()
    stable_distance = stable_buildings.geometry.centroid.distance(narrow_union).mean()
    assert priority_distance < stable_distance


def test_r01_geojson_outputs_have_valid_wgs84_geometry() -> None:
    client.post("/api/simulation/generate", json={"seed": 42})
    buildings = client.get("/api/renewal/R-01/buildings").json()

    geometries = [shape(feature["geometry"]) for feature in buildings["features"]]
    frame = gpd.GeoDataFrame(geometry=geometries, crs=BASE_CRS).to_crs(GRID_CRS)

    assert frame.geometry.is_valid.all()
    assert frame.geometry.area.min() > 0
