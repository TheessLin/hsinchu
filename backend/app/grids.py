from functools import lru_cache
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry.base import BaseGeometry
from shapely.geometry import box

BASE_CRS = "EPSG:4326"
GRID_CRS = "EPSG:3826"
GRID_SIZE_METERS = 500
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOUNDARY_PATH = PROJECT_ROOT / "data" / "base" / "hsinchu_city_administrative_boundary.geojson"
DISTRICTS_PATH = PROJECT_ROOT / "data" / "base" / "hsinchu_city_district_boundaries.geojson"


def load_study_boundary() -> gpd.GeoDataFrame:
    boundary = gpd.read_file(BOUNDARY_PATH)
    if boundary.crs is None:
        boundary = boundary.set_crs(BASE_CRS)

    return boundary.to_crs(BASE_CRS)


def load_district_boundaries() -> gpd.GeoDataFrame:
    districts = gpd.read_file(DISTRICTS_PATH)
    if districts.crs is None:
        districts = districts.set_crs(BASE_CRS)

    return districts.to_crs(BASE_CRS)


def get_boundary_geojson() -> dict[str, Any]:
    districts = load_district_boundaries()
    return _geo_dataframe_to_feature_collection(districts)


@lru_cache(maxsize=1)
def get_grid_geojson() -> dict[str, Any]:
    grids = generate_analysis_grids()
    return _geo_dataframe_to_feature_collection(grids)


def generate_analysis_grids() -> gpd.GeoDataFrame:
    districts = load_district_boundaries().to_crs(GRID_CRS)
    boundary_geometry = districts.geometry.union_all()
    min_x, min_y, max_x, max_y = boundary_geometry.bounds

    cells: list[dict[str, Any]] = []
    grid_index = 1
    x = _floor_to_grid(min_x)

    while x < max_x:
        y = _floor_to_grid(min_y)
        while y < max_y:
            cell = box(x, y, x + GRID_SIZE_METERS, y + GRID_SIZE_METERS)
            if cell.intersects(boundary_geometry):
                centroid = cell.centroid
                district_type = classify_district_type(cell, districts)
                land_use_type = classify_land_use_type(
                    centroid.x,
                    centroid.y,
                    boundary_geometry.centroid.x,
                    boundary_geometry.centroid.y,
                    district_type,
                )
                cells.append(
                    {
                        "grid_id": f"HC-GRID-{grid_index:04d}",
                        "centroid_projected_x": centroid.x,
                        "centroid_projected_y": centroid.y,
                        "district_type": district_type,
                        "land_use_type": land_use_type,
                        "geometry": cell,
                    }
                )
                grid_index += 1
            y += GRID_SIZE_METERS
        x += GRID_SIZE_METERS

    grid_frame = gpd.GeoDataFrame(cells, geometry="geometry", crs=GRID_CRS)
    grid_frame = grid_frame.to_crs(BASE_CRS)
    centroids = grid_frame.to_crs(GRID_CRS).geometry.centroid
    centroid_frame = gpd.GeoSeries(centroids, crs=GRID_CRS).to_crs(BASE_CRS)
    grid_frame["centroid_x"] = centroid_frame.x.round(6)
    grid_frame["centroid_y"] = centroid_frame.y.round(6)
    grid_frame = grid_frame.drop(columns=["centroid_projected_x", "centroid_projected_y"])

    return grid_frame[["grid_id", "centroid_x", "centroid_y", "district_type", "land_use_type", "geometry"]]


def classify_district_type(cell: BaseGeometry, districts: gpd.GeoDataFrame) -> str:
    intersections = districts.geometry.intersection(cell)
    best_match_index = intersections.area.idxmax()
    district_name = districts.loc[best_match_index, "district_name"]

    return str(district_name)


def classify_land_use_type(x: float, y: float, center_x: float, center_y: float, district_type: str) -> str:
    distance_to_center = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5

    if district_type == "香山區":
        if y < center_y - 4200:
            return "綠地與開放空間"
        return "產業與倉儲"
    if district_type == "東區":
        if distance_to_center <= 2400:
            return "商業混合使用"
        return "住宅與科技服務混合"
    if district_type == "北區":
        if distance_to_center <= 2200:
            return "商業混合使用"
        return "住宅混合使用"
    if distance_to_center <= 2200:
        return "商業混合使用"
    return "公共服務與住宅"


def _floor_to_grid(value: float) -> float:
    return value - (value % GRID_SIZE_METERS)


def _geo_dataframe_to_feature_collection(frame: gpd.GeoDataFrame) -> dict[str, Any]:
    return frame.to_crs(BASE_CRS).__geo_interface__
