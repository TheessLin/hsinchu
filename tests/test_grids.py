from fastapi.testclient import TestClient

from app.grids import GRID_CRS, GRID_SIZE_METERS, generate_analysis_grids, load_district_boundaries, load_study_boundary
from app.main import app


def test_generate_analysis_grids_has_required_fields() -> None:
    grids = generate_analysis_grids()

    assert len(grids) > 0
    assert list(grids.columns) == [
        "grid_id",
        "centroid_x",
        "centroid_y",
        "district_type",
        "land_use_type",
        "geometry",
    ]
    assert grids["grid_id"].is_unique
    assert grids.iloc[0]["grid_id"] == "HC-GRID-0001"
    assert grids.crs.to_string() == "EPSG:4326"


def test_generated_grids_intersect_study_boundary_and_are_500m_cells() -> None:
    boundary = load_study_boundary().to_crs(GRID_CRS)
    boundary_geometry = boundary.geometry.union_all()
    grids = generate_analysis_grids().to_crs(GRID_CRS)

    assert grids.geometry.intersects(boundary_geometry).all()

    min_width = grids.bounds["maxx"] - grids.bounds["minx"]
    min_height = grids.bounds["maxy"] - grids.bounds["miny"]
    assert min_width.round(6).eq(GRID_SIZE_METERS).all()
    assert min_height.round(6).eq(GRID_SIZE_METERS).all()

    grid_union = grids.geometry.union_all()
    outside_area = grid_union.difference(boundary_geometry).area
    allowed_outside_area = boundary_geometry.buffer(GRID_SIZE_METERS).difference(boundary_geometry).area
    assert outside_area < allowed_outside_area


def test_grid_centroids_and_categories_are_populated() -> None:
    grids = generate_analysis_grids()

    assert grids["centroid_x"].between(120.87, 121.04).all()
    assert grids["centroid_y"].between(24.70, 24.87).all()
    assert set(grids["district_type"]) == {"北區", "東區", "香山區"}
    assert {"商業混合使用", "產業與倉儲", "住宅與科技服務混合"} <= set(grids["land_use_type"])


def test_grids_api_returns_geojson_feature_collection() -> None:
    client = TestClient(app)

    response = client.get("/api/grids")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == len(generate_analysis_grids())
    first_feature = payload["features"][0]
    assert first_feature["type"] == "Feature"
    assert first_feature["geometry"]["type"] == "Polygon"
    assert {
        "grid_id",
        "centroid_x",
        "centroid_y",
        "district_type",
        "land_use_type",
    } <= set(first_feature["properties"])


def test_boundary_api_returns_geojson_feature_collection() -> None:
    client = TestClient(app)

    response = client.get("/api/boundary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 3
    assert {feature["properties"]["district_name"] for feature in payload["features"]} == {"北區", "東區", "香山區"}
    assert payload["features"][0]["geometry"]["type"] in {"Polygon", "MultiPolygon"}


def test_district_boundaries_have_three_hsinchu_districts() -> None:
    districts = load_district_boundaries()

    assert len(districts) == 3
    assert set(districts["district_name"]) == {"北區", "東區", "香山區"}
    assert districts.crs.to_string() == "EPSG:4326"
