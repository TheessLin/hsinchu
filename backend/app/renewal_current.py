from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box, mapping
from shapely.geometry.base import BaseGeometry

from app.grids import BASE_CRS, GRID_CRS, generate_analysis_grids
from app.phase2 import SYNTHETIC_DATA_DISCLAIMER, get_phase2_candidate_detail
from app.simulation import get_simulation_state

CURRENT_YEAR = 2026
R01_CANDIDATE_ID = "R-01"


@dataclass(frozen=True)
class RenewalCurrentData:
    seed: int
    blocks: gpd.GeoDataFrame
    buildings: gpd.GeoDataFrame
    roads: gpd.GeoDataFrame
    facilities: gpd.GeoDataFrame


def get_r01_current_data() -> RenewalCurrentData:
    state = get_simulation_state()
    return generate_r01_current_data(seed=state.seed)


def generate_r01_current_data(seed: int = 42) -> RenewalCurrentData:
    rng = np.random.default_rng(seed + 201)
    candidate = get_phase2_candidate_detail(R01_CANDIDATE_ID)
    if candidate is None:
        raise ValueError("R-01 candidate is not available.")

    blocks = _generate_blocks(candidate["grid_ids"], rng)
    buildings = _generate_buildings(blocks, rng)
    roads = _generate_roads(blocks, rng)
    facilities = _generate_facilities(blocks, rng)
    return RenewalCurrentData(seed=seed, blocks=blocks, buildings=buildings, roads=roads, facilities=facilities)


def get_r01_current_payload() -> dict[str, Any]:
    current = get_r01_current_data()
    return {
        "candidate_id": R01_CANDIDATE_ID,
        "seed": current.seed,
        "data_type": "synthetic",
        "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
        "blocks": to_feature_collection(current.blocks, current.seed, "blocks"),
        "buildings": to_feature_collection(current.buildings, current.seed, "buildings"),
        "roads": to_feature_collection(current.roads, current.seed, "roads"),
        "facilities": to_feature_collection(current.facilities, current.seed, "facilities"),
    }


def get_r01_blocks_geojson() -> dict[str, Any]:
    current = get_r01_current_data()
    return to_feature_collection(current.blocks, current.seed, "blocks")


def get_r01_buildings_geojson() -> dict[str, Any]:
    current = get_r01_current_data()
    return to_feature_collection(current.buildings, current.seed, "buildings")


def get_r01_roads_geojson() -> dict[str, Any]:
    current = get_r01_current_data()
    return to_feature_collection(current.roads, current.seed, "roads")


def get_r01_facilities_geojson() -> dict[str, Any]:
    current = get_r01_current_data()
    return to_feature_collection(current.facilities, current.seed, "facilities")


def to_feature_collection(frame: gpd.GeoDataFrame, seed: int, layer: str) -> dict[str, Any]:
    output = frame.to_crs(BASE_CRS)
    features: list[dict[str, Any]] = []
    for _, row in output.iterrows():
        properties = {
            key: value.item() if hasattr(value, "item") else value
            for key, value in row.drop(labels=["geometry"]).to_dict().items()
        }
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(row.geometry),
            }
        )

    return {
        "type": "FeatureCollection",
        "metadata": {
            "candidate_id": R01_CANDIDATE_ID,
            "layer": layer,
            "seed": seed,
            "data_type": "synthetic",
            "crs": BASE_CRS,
        },
        "features": features,
    }


def _generate_blocks(grid_ids: list[str], rng: np.random.Generator) -> gpd.GeoDataFrame:
    grids = generate_analysis_grids().to_crs(GRID_CRS)
    blocks = grids[grids["grid_id"].isin(grid_ids)].sort_values("grid_id").reset_index(drop=True).copy()
    old_focus = _old_focus_point(blocks.geometry.union_all())

    records: list[dict[str, Any]] = []
    max_distance = max(float(blocks.geometry.centroid.distance(old_focus).max()), 1.0)
    for index, row in blocks.iterrows():
        geometry = row.geometry
        centroid = geometry.centroid
        old_intensity = _bounded(
            1 - (centroid.distance(old_focus) / max_distance) + rng.normal(0, 0.08),
            0,
            1,
        )
        dominant_use = _dominant_use(old_intensity, index)
        building_coverage = round(_bounded(0.34 + 0.32 * old_intensity + rng.normal(0, 0.035), 0.25, 0.78), 3)
        floor_area_ratio = round(_bounded(0.85 + 2.2 * old_intensity + rng.normal(0, 0.18), 0.6, 3.8), 2)
        open_space_ratio = round(_bounded(0.42 - 0.25 * old_intensity + rng.normal(0, 0.025), 0.08, 0.5), 3)
        records.append(
            {
                "block_id": f"R01-BLOCK-{index + 1:03d}",
                "source_grid_id": row["grid_id"],
                "area_m2": round(float(geometry.area), 2),
                "dominant_use": dominant_use,
                "building_coverage_ratio": building_coverage,
                "floor_area_ratio": floor_area_ratio,
                "open_space_ratio": open_space_ratio,
                "old_intensity": round(old_intensity, 4),
                "geometry": geometry,
            }
        )

    return gpd.GeoDataFrame(records, geometry="geometry", crs=GRID_CRS)


def _generate_buildings(blocks: gpd.GeoDataFrame, rng: np.random.Generator) -> gpd.GeoDataFrame:
    target_count = int(rng.integers(85, 121))
    weights = blocks["area_m2"].to_numpy() * (0.65 + blocks["building_coverage_ratio"].to_numpy()) * (
        0.8 + blocks["old_intensity"].to_numpy()
    )
    raw_counts = weights / weights.sum() * target_count
    counts = np.floor(raw_counts).astype(int)
    for index in np.argsort(raw_counts - counts)[::-1][: target_count - int(counts.sum())]:
        counts[index] += 1

    records: list[dict[str, Any]] = []
    building_index = 1
    for block_index, block in blocks.iterrows():
        count = int(counts[block_index])
        if count <= 0:
            continue

        footprints = _building_footprints_in_block(block.geometry, count, rng)
        for footprint in footprints:
            old_intensity = float(block["old_intensity"])
            use_type = _building_use_type(str(block["dominant_use"]), old_intensity, rng)
            age = _building_age(old_intensity, rng)
            floors = _building_floors(use_type, old_intensity, rng)
            floor_area = float(footprint.area) * floors
            residential_units = _residential_units(use_type, floor_area, rng)
            commercial_floor_area = round(floor_area * _commercial_share(use_type, rng), 2)
            estimated_population = int(round(residential_units * rng.uniform(2.0, 2.6)))
            parking_spaces = _parking_spaces(residential_units, commercial_floor_area, old_intensity, rng)
            records.append(
                {
                    "building_id": f"R01-BLDG-{building_index:03d}",
                    "block_id": block["block_id"],
                    "floors": floors,
                    "height_m": round(floors * 3.2, 1),
                    "construction_year": CURRENT_YEAR - age,
                    "age": age,
                    "use_type": use_type,
                    "residential_units": residential_units,
                    "commercial_floor_area": commercial_floor_area,
                    "estimated_population": estimated_population,
                    "parking_spaces": parking_spaces,
                    "renewal_status": _renewal_status(age, old_intensity),
                    "geometry": footprint,
                }
            )
            building_index += 1

    return gpd.GeoDataFrame(records, geometry="geometry", crs=GRID_CRS)


def _generate_roads(blocks: gpd.GeoDataFrame, rng: np.random.Generator) -> gpd.GeoDataFrame:
    union = blocks.geometry.union_all()
    old_focus = _old_focus_point(union)
    min_x, min_y, max_x, max_y = union.bounds
    x_values = sorted({round(value, 3) for geom in blocks.geometry for value in (geom.bounds[0], geom.bounds[2])})
    y_values = sorted({round(value, 3) for geom in blocks.geometry for value in (geom.bounds[1], geom.bounds[3])})
    road_lines: list[BaseGeometry] = []
    road_lines.extend(LineString([(x, min_y), (x, max_y)]).intersection(union) for x in x_values)
    road_lines.extend(LineString([(min_x, y), (max_x, y)]).intersection(union) for y in y_values)

    records: list[dict[str, Any]] = []
    road_index = 1
    max_distance = max(max_x - min_x, max_y - min_y, 1)
    for geometry in road_lines:
        for segment in _line_segments(geometry):
            if segment.length < 120:
                continue
            old_score = _bounded(1 - segment.centroid.distance(old_focus) / max_distance + rng.normal(0, 0.08), 0, 1)
            width = round(_bounded(11.5 - 6.2 * old_score + rng.normal(0, 0.65), 3.5, 14.5), 1)
            sidewalk_width = round(_bounded(width * 0.18 - 0.55 * old_score + rng.normal(0, 0.08), 0.2, 3.2), 1)
            records.append(
                {
                    "road_id": f"R01-ROAD-{road_index:03d}",
                    "width_m": width,
                    "road_type": _road_type(width),
                    "sidewalk_width_m": sidewalk_width,
                    "emergency_accessible": bool(width >= 6.0),
                    "pedestrian_capacity": int(round(segment.length * max(sidewalk_width, 0.2) * 1.35)),
                    "geometry": segment,
                }
            )
            road_index += 1

    return gpd.GeoDataFrame(records, geometry="geometry", crs=GRID_CRS)


def _generate_facilities(blocks: gpd.GeoDataFrame, rng: np.random.Generator) -> gpd.GeoDataFrame:
    facility_plan = [
        ("park", 2),
        ("shelter", 2),
        ("parking", 3),
        ("bus_stop", 6),
        ("bike_station", 4),
        ("clinic", 2),
        ("childcare", 2),
        ("elderly_service", 2),
        ("market", 2),
    ]
    low_old_blocks = blocks.sort_values("old_intensity", ascending=True).reset_index(drop=True)
    high_old_blocks = blocks.sort_values("old_intensity", ascending=False).reset_index(drop=True)
    mixed_blocks = blocks.sample(frac=1, random_state=int(rng.integers(1, 1_000_000))).reset_index(drop=True)

    records: list[dict[str, Any]] = []
    facility_index = 1
    for facility_type, count in facility_plan:
        pool = low_old_blocks if facility_type in {"park", "shelter"} else high_old_blocks if facility_type in {"market", "clinic"} else mixed_blocks
        for item_index in range(count):
            block = pool.iloc[(item_index * 3 + facility_index) % len(pool)]
            point = _point_inside_block(block.geometry, rng)
            records.append(
                {
                    "facility_id": f"R01-FAC-{facility_index:03d}",
                    "facility_type": facility_type,
                    "capacity": _facility_capacity(facility_type, rng),
                    "service_radius_m": _service_radius(facility_type),
                    "geometry": point,
                }
            )
            facility_index += 1

    return gpd.GeoDataFrame(records, geometry="geometry", crs=GRID_CRS)


def _building_footprints_in_block(block_geometry: Polygon, count: int, rng: np.random.Generator) -> list[Polygon]:
    min_x, min_y, max_x, max_y = block_geometry.bounds
    usable_width = max_x - min_x - 42
    usable_height = max_y - min_y - 42
    columns = int(np.ceil(np.sqrt(count * usable_width / max(usable_height, 1))))
    rows = int(np.ceil(count / max(columns, 1)))
    cell_width = usable_width / max(columns, 1)
    cell_height = usable_height / max(rows, 1)
    footprints: list[Polygon] = []

    for index in range(count):
        row = index // columns
        column = index % columns
        center_x = min_x + 21 + (column + 0.5) * cell_width + rng.normal(0, min(cell_width * 0.08, 8))
        center_y = min_y + 21 + (row + 0.5) * cell_height + rng.normal(0, min(cell_height * 0.08, 8))
        width = _bounded(cell_width * rng.uniform(0.38, 0.62), 14, 52)
        depth = _bounded(cell_height * rng.uniform(0.36, 0.58), 12, 46)
        footprint = box(center_x - width / 2, center_y - depth / 2, center_x + width / 2, center_y + depth / 2)
        if not block_geometry.contains(footprint):
            footprint = footprint.intersection(block_geometry.buffer(-6))
        if footprint.is_empty or not isinstance(footprint, Polygon) or footprint.area < 100:
            continue
        footprints.append(footprint)

    return footprints


def _point_inside_block(block_geometry: Polygon, rng: np.random.Generator) -> Point:
    min_x, min_y, max_x, max_y = block_geometry.bounds
    for _attempt in range(80):
        point = Point(rng.uniform(min_x + 30, max_x - 30), rng.uniform(min_y + 30, max_y - 30))
        if block_geometry.contains(point):
            return point
    return block_geometry.representative_point()


def _line_segments(geometry: BaseGeometry) -> list[LineString]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, LineString):
        return [geometry]
    if isinstance(geometry, MultiLineString):
        return [segment for segment in geometry.geoms if segment.length > 0]
    return []


def _old_focus_point(geometry: BaseGeometry) -> Point:
    min_x, min_y, max_x, max_y = geometry.bounds
    return Point(min_x + (max_x - min_x) * 0.34, min_y + (max_y - min_y) * 0.42)


def _dominant_use(old_intensity: float, index: int) -> str:
    if old_intensity >= 0.68:
        return "old_mixed_residential"
    if old_intensity >= 0.5:
        return "mixed_use"
    if index % 7 == 0:
        return "commercial"
    return "residential"


def _building_use_type(dominant_use: str, old_intensity: float, rng: np.random.Generator) -> str:
    if dominant_use == "commercial":
        return "commercial" if rng.random() < 0.7 else "mixed_use"
    if dominant_use in {"mixed_use", "old_mixed_residential"}:
        return "mixed_use" if rng.random() < 0.48 + old_intensity * 0.22 else "residential"
    return "residential" if rng.random() < 0.86 else "mixed_use"


def _building_age(old_intensity: float, rng: np.random.Generator) -> int:
    return int(round(_bounded(12 + 43 * old_intensity + rng.normal(0, 6), 3, 65)))


def _building_floors(use_type: str, old_intensity: float, rng: np.random.Generator) -> int:
    base = 4.0 if use_type == "residential" else 5.5 if use_type == "mixed_use" else 6.5
    return int(round(_bounded(base + rng.normal(0, 1.2) - 1.2 * old_intensity, 1, 14)))


def _residential_units(use_type: str, floor_area: float, rng: np.random.Generator) -> int:
    if use_type == "commercial":
        return 0
    residential_share = 0.92 if use_type == "residential" else 0.58
    return int(max(1, round(floor_area * residential_share / rng.uniform(78, 105))))


def _commercial_share(use_type: str, rng: np.random.Generator) -> float:
    if use_type == "commercial":
        return rng.uniform(0.78, 0.96)
    if use_type == "mixed_use":
        return rng.uniform(0.22, 0.42)
    return rng.uniform(0, 0.06)


def _parking_spaces(residential_units: int, commercial_floor_area: float, old_intensity: float, rng: np.random.Generator) -> int:
    demand_basis = residential_units * rng.uniform(0.35, 0.85) + commercial_floor_area / rng.uniform(85, 125)
    return int(round(max(0, demand_basis * (1 - old_intensity * 0.48))))


def _renewal_status(age: int, old_intensity: float) -> str:
    if age >= 42 and old_intensity >= 0.62:
        return "priority"
    if age >= 32 or old_intensity >= 0.52:
        return "monitor"
    return "stable"


def _road_type(width: float) -> str:
    if width < 5.0:
        return "alley"
    if width < 8.0:
        return "local"
    if width < 11.5:
        return "collector"
    return "arterial"


def _facility_capacity(facility_type: str, rng: np.random.Generator) -> int:
    ranges = {
        "park": (120, 420),
        "shelter": (180, 520),
        "parking": (35, 120),
        "bus_stop": (80, 180),
        "bike_station": (20, 70),
        "clinic": (90, 240),
        "childcare": (35, 90),
        "elderly_service": (30, 80),
        "market": (160, 420),
    }
    lower, upper = ranges[facility_type]
    return int(rng.integers(lower, upper + 1))


def _service_radius(facility_type: str) -> int:
    return {
        "park": 350,
        "shelter": 450,
        "parking": 250,
        "bus_stop": 300,
        "bike_station": 250,
        "clinic": 650,
        "childcare": 500,
        "elderly_service": 500,
        "market": 450,
    }[facility_type]


def _bounded(value: float, lower: float, upper: float) -> float:
    return min(max(float(value), lower), upper)
