from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Literal

import geopandas as gpd
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import Point, Polygon, box, mapping
from shapely.geometry.base import BaseGeometry

from app.grids import BASE_CRS, GRID_CRS
from app.renewal_current import R01_CANDIDATE_ID, RenewalCurrentData, get_r01_current_data

ScenarioId = Literal["0", "A", "B", "C"]


class ScenarioParameterValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    removal_count: int = Field(default=8, ge=0, le=30)
    housing_building_count: int = Field(default=4, ge=0, le=5)
    housing_floors: int = Field(default=12, ge=6, le=18)
    underground_parking_per_building: int = Field(default=70, ge=0, le=180)
    minimum_open_space_ratio: float = Field(default=0.22, ge=0, le=0.6)
    resilience_housing_building_count: int = Field(default=1, ge=0, le=3)
    park_count: int = Field(default=1, ge=0, le=4)
    disaster_plaza_count: int = Field(default=1, ge=0, le=3)
    emergency_route_count: int = Field(default=3, ge=0, le=8)
    green_coverage_target: float = Field(default=0.38, ge=0, le=0.8)
    eldercare_facilities: int = Field(default=1, ge=0, le=4)
    childcare_facilities: int = Field(default=1, ge=0, le=4)
    mixed_use_building_count: int = Field(default=3, ge=0, le=5)
    commercial_floor_area_multiplier: float = Field(default=1.45, ge=1, le=3)
    sidewalk_width_gain_m: float = Field(default=1.2, ge=0, le=3)
    new_bus_stops: int = Field(default=1, ge=0, le=4)
    new_bike_stations: int = Field(default=1, ge=0, le=4)
    shared_parking_spaces: int = Field(default=80, ge=0, le=300)
    daytime_population_multiplier: float = Field(default=1.25, ge=1, le=2.5)


class ScenarioRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_values: ScenarioParameterValues = Field(default_factory=ScenarioParameterValues)


class ScenarioResult(BaseModel):
    scenario_id: ScenarioId
    scenario_name: str
    description: str
    assumptions: list[str]
    removed_building_ids: list[str]
    added_buildings: list[dict[str, Any]]
    modified_roads: list[dict[str, Any]]
    added_facilities: list[dict[str, Any]]
    parameter_values: dict[str, int | float]
    created_at: str
    simulation_seed: int


SCENARIO_DEFINITIONS: dict[ScenarioId, dict[str, Any]] = {
    "0": {
        "scenario_name": "Current",
        "description": "保留 R-01 現況模擬資料，不進行拆除、新建或道路設施調整。",
        "assumptions": ["現況方案作為其他 Scenario 的比較基準。", "所有資料皆為 Synthetic Data。"],
    },
    "A": {
        "scenario_name": "Housing",
        "description": "移除部分老舊建物，新增中高層住宅、住宅戶數、地下停車與基本開放空間。",
        "assumptions": ["優先選取高屋齡且 renewal_status 為 priority 的建物。", "新建住宅以街廓內 LOD1 量體表示。"],
    },
    "B": {
        "scenario_name": "Resilience",
        "description": "降低住宅新增量，新增公園、防災廣場、高齡與幼兒設施，並拓寬消防動線。",
        "assumptions": ["優先改善狹窄道路及設施不足街廓。", "綠覆率以參數目標作為設施設計假設。"],
    },
    "C": {
        "scenario_name": "TransitCommercial",
        "description": "提高混合使用與商業量體，改善人行道，新增公車站、自行車站與共享停車。",
        "assumptions": ["優先選取交通與商業活動潛力較高的街廓。", "日間人口提升由混合使用及商業面積推估。"],
    },
}

_scenario_run_records: list[dict[str, Any]] = []


def list_r01_scenarios() -> dict[str, Any]:
    records = [_build_r01_scenario(scenario_id, ScenarioRunRequest()) for scenario_id in ["0", "A", "B", "C"]]
    return {
        "candidate_id": R01_CANDIDATE_ID,
        "parameter_schema": ScenarioParameterValues.model_json_schema(),
        "count": len(records),
        "records": records,
    }


def get_r01_scenario(scenario_id: str) -> dict[str, Any] | None:
    normalized = normalize_scenario_id(scenario_id)
    if normalized is None:
        return None
    return _build_r01_scenario(normalized, ScenarioRunRequest())


def run_r01_scenario(scenario_id: ScenarioId, request: ScenarioRunRequest) -> dict[str, Any]:
    result = _build_r01_scenario(scenario_id, request)
    json_ready_result = _json_ready(result)
    _scenario_run_records.append(deepcopy(json_ready_result))
    return json_ready_result


def _build_r01_scenario(scenario_id: ScenarioId, request: ScenarioRunRequest) -> dict[str, Any]:
    current = get_r01_current_data()
    parameters = _parameters_for_scenario(scenario_id, request.parameter_values)
    return _json_ready(_build_scenario_result(scenario_id, current, parameters))


def get_scenario_run_records() -> list[dict[str, Any]]:
    return deepcopy(_scenario_run_records)


def normalize_scenario_id(scenario_id: str) -> ScenarioId | None:
    normalized = scenario_id.upper()
    if normalized in {"CURRENT", "SCENARIO_0"}:
        return "0"
    if normalized in SCENARIO_DEFINITIONS:
        return normalized  # type: ignore[return-value]
    return None


def _parameters_for_scenario(scenario_id: ScenarioId, parameters: ScenarioParameterValues) -> ScenarioParameterValues:
    data = parameters.model_dump()
    if scenario_id == "0":
        data.update(
            {
                "removal_count": 0,
                "housing_building_count": 0,
                "resilience_housing_building_count": 0,
                "mixed_use_building_count": 0,
                "park_count": 0,
                "disaster_plaza_count": 0,
                "emergency_route_count": 0,
                "eldercare_facilities": 0,
                "childcare_facilities": 0,
                "new_bus_stops": 0,
                "new_bike_stations": 0,
                "shared_parking_spaces": 0,
            }
        )
    elif scenario_id == "B":
        data["housing_building_count"] = data["resilience_housing_building_count"]
    elif scenario_id == "C":
        data["housing_building_count"] = 0
        data["park_count"] = 0
        data["disaster_plaza_count"] = 0
        data["eldercare_facilities"] = 0
        data["childcare_facilities"] = 0
    return ScenarioParameterValues(**data)


def _build_scenario_result(scenario_id: ScenarioId, current: RenewalCurrentData, parameters: ScenarioParameterValues) -> dict[str, Any]:
    definition = SCENARIO_DEFINITIONS[scenario_id]
    removed_building_ids = _removed_building_ids(current, parameters.removal_count)
    rng = np.random.default_rng(_scenario_seed(current.seed, scenario_id, parameters))

    if scenario_id == "0":
        added_buildings: list[dict[str, Any]] = []
        modified_roads: list[dict[str, Any]] = []
        added_facilities: list[dict[str, Any]] = []
    elif scenario_id == "A":
        added_buildings = _added_housing_buildings(current, parameters, rng, removed_building_ids)
        modified_roads = []
        added_facilities = _added_open_space_facilities(current, parameters, rng)
    elif scenario_id == "B":
        added_buildings = _added_resilience_buildings(current, parameters, rng, removed_building_ids)
        modified_roads = _modified_emergency_roads(current, parameters)
        added_facilities = _added_resilience_facilities(current, parameters, rng)
    else:
        added_buildings = _added_transit_commercial_buildings(current, parameters, rng, removed_building_ids)
        modified_roads = _modified_pedestrian_roads(current, parameters)
        added_facilities = _added_transit_facilities(current, parameters, rng)

    return ScenarioResult(
        scenario_id=scenario_id,
        scenario_name=str(definition["scenario_name"]),
        description=str(definition["description"]),
        assumptions=list(definition["assumptions"]),
        removed_building_ids=removed_building_ids,
        added_buildings=added_buildings,
        modified_roads=modified_roads,
        added_facilities=added_facilities,
        parameter_values=parameters.model_dump(),
        created_at=_deterministic_created_at(current.seed, scenario_id, parameters),
        simulation_seed=current.seed,
    ).model_dump()


def _removed_building_ids(current: RenewalCurrentData, count: int) -> list[str]:
    if count <= 0:
        return []
    priority_order = {"priority": 0, "monitor": 1, "stable": 2}
    frame = current.buildings.copy()
    frame["_priority_order"] = frame["renewal_status"].map(priority_order).fillna(9)
    frame = frame.sort_values(["_priority_order", "age", "building_id"], ascending=[True, False, True])
    return [str(building_id) for building_id in frame.head(count)["building_id"].tolist()]


def _added_housing_buildings(
    current: RenewalCurrentData,
    parameters: ScenarioParameterValues,
    rng: np.random.Generator,
    removed_building_ids: list[str],
) -> list[dict[str, Any]]:
    count = max(3, min(parameters.housing_building_count, 5)) if parameters.housing_building_count > 0 else 0
    blocks = _target_blocks_from_removed_buildings(current, removed_building_ids, count)
    return [
        _new_building_record(
            scenario_id="A",
            index=index,
            block=blocks.iloc[index % len(blocks)],
            rng=rng,
            floors=parameters.housing_floors + int(rng.integers(-1, 2)),
            use_type="residential",
            units_per_floor=12,
            parking_spaces=parameters.underground_parking_per_building,
            commercial_ratio=0.04,
        )
        for index in range(count)
    ]


def _added_resilience_buildings(
    current: RenewalCurrentData,
    parameters: ScenarioParameterValues,
    rng: np.random.Generator,
    removed_building_ids: list[str],
) -> list[dict[str, Any]]:
    count = parameters.resilience_housing_building_count
    if count <= 0:
        return []
    blocks = _target_blocks_from_removed_buildings(current, removed_building_ids, count)
    return [
        _new_building_record(
            scenario_id="B",
            index=index,
            block=blocks.iloc[index % len(blocks)],
            rng=rng,
            floors=max(5, parameters.housing_floors - 4 + int(rng.integers(-1, 2))),
            use_type="residential",
            units_per_floor=5,
            parking_spaces=max(20, parameters.underground_parking_per_building // 2),
            commercial_ratio=0.02,
        )
        for index in range(count)
    ]


def _added_transit_commercial_buildings(
    current: RenewalCurrentData,
    parameters: ScenarioParameterValues,
    rng: np.random.Generator,
    removed_building_ids: list[str],
) -> list[dict[str, Any]]:
    count = parameters.mixed_use_building_count
    if count <= 0:
        return []
    blocks = _target_blocks_from_removed_buildings(current, removed_building_ids, count)
    return [
        _new_building_record(
            scenario_id="C",
            index=index,
            block=blocks.iloc[index % len(blocks)],
            rng=rng,
            floors=max(7, parameters.housing_floors - 2 + int(rng.integers(-1, 3))),
            use_type="mixed_use",
            units_per_floor=4,
            parking_spaces=round(parameters.shared_parking_spaces / max(count, 1)),
            commercial_ratio=min(0.65, 0.34 * parameters.commercial_floor_area_multiplier),
            daytime_population_multiplier=parameters.daytime_population_multiplier,
        )
        for index in range(count)
    ]


def _new_building_record(
    scenario_id: ScenarioId,
    index: int,
    block: Any,
    rng: np.random.Generator,
    floors: int,
    use_type: str,
    units_per_floor: int,
    parking_spaces: int,
    commercial_ratio: float,
    daytime_population_multiplier: float = 1.0,
) -> dict[str, Any]:
    geometry = _new_building_geometry(block.geometry, index, rng)
    floors = max(1, min(int(floors), 18))
    footprint_area = float(geometry.area)
    residential_units = 0 if use_type == "commercial" else max(0, floors * units_per_floor)
    commercial_floor_area = round(footprint_area * floors * commercial_ratio, 2)
    estimated_population = int(round(residential_units * 2.25))
    daytime_population = int(round((estimated_population * 0.45 + commercial_floor_area / 18) * daytime_population_multiplier))
    return {
        "building_id": f"R01-S{scenario_id}-BLDG-{index + 1:02d}",
        "block_id": str(block["block_id"]),
        "geometry": _to_wgs84_geometry(geometry),
        "floors": floors,
        "height_m": round(floors * 3.2, 1),
        "use_type": use_type,
        "residential_units": residential_units,
        "commercial_floor_area": commercial_floor_area,
        "estimated_population": estimated_population,
        "daytime_population": daytime_population,
        "parking_spaces": int(parking_spaces),
        "change_type": "added",
    }


def _modified_emergency_roads(current: RenewalCurrentData, parameters: ScenarioParameterValues) -> list[dict[str, Any]]:
    roads = current.roads.sort_values(["emergency_accessible", "width_m", "road_id"], ascending=[True, True, True])
    selected = roads.head(parameters.emergency_route_count)
    return [_modified_road_record(row, max(6.5, float(row["width_m"]) + 2.2), max(1.5, float(row["sidewalk_width_m"]) + 0.5)) for _, row in selected.iterrows()]


def _modified_pedestrian_roads(current: RenewalCurrentData, parameters: ScenarioParameterValues) -> list[dict[str, Any]]:
    roads = current.roads.sort_values(["sidewalk_width_m", "width_m", "road_id"], ascending=[True, True, True])
    selected = roads.head(max(3, parameters.new_bus_stops + parameters.new_bike_stations + 2))
    return [
        _modified_road_record(
            row,
            max(float(row["width_m"]), min(14.5, float(row["width_m"]) + 0.4)),
            min(3.5, float(row["sidewalk_width_m"]) + parameters.sidewalk_width_gain_m),
        )
        for _, row in selected.iterrows()
    ]


def _modified_road_record(row: Any, width_m: float, sidewalk_width_m: float) -> dict[str, Any]:
    return {
        "road_id": str(row["road_id"]),
        "geometry": _to_wgs84_geometry(row.geometry),
        "width_m": round(width_m, 1),
        "road_type": _road_type(width_m),
        "sidewalk_width_m": round(sidewalk_width_m, 1),
        "emergency_accessible": bool(width_m >= 6.0),
        "pedestrian_capacity": int(round(row.geometry.length * max(sidewalk_width_m, 0.2) * 1.35)),
        "change_type": "modified",
    }


def _added_open_space_facilities(current: RenewalCurrentData, parameters: ScenarioParameterValues, rng: np.random.Generator) -> list[dict[str, Any]]:
    return [
        _new_facility_record("A", 0, "open_space", current.blocks.sort_values("old_intensity", ascending=False).iloc[0], rng, 180, 250),
        _new_facility_record("A", 1, "underground_parking", current.blocks.sort_values("old_intensity", ascending=False).iloc[1], rng, parameters.underground_parking_per_building, 220),
    ]


def _added_resilience_facilities(current: RenewalCurrentData, parameters: ScenarioParameterValues, rng: np.random.Generator) -> list[dict[str, Any]]:
    low_open_blocks = current.blocks.sort_values(["open_space_ratio", "old_intensity"], ascending=[True, False]).reset_index(drop=True)
    records: list[dict[str, Any]] = []
    index = 0
    for _ in range(parameters.park_count):
        records.append(_new_facility_record("B", index, "park", low_open_blocks.iloc[index % len(low_open_blocks)], rng, 420, 420))
        index += 1
    for _ in range(parameters.disaster_plaza_count):
        records.append(_new_facility_record("B", index, "disaster_plaza", low_open_blocks.iloc[index % len(low_open_blocks)], rng, 520, 500))
        index += 1
    for _ in range(parameters.eldercare_facilities):
        records.append(_new_facility_record("B", index, "elderly_service", low_open_blocks.iloc[index % len(low_open_blocks)], rng, 80, 500))
        index += 1
    for _ in range(parameters.childcare_facilities):
        records.append(_new_facility_record("B", index, "childcare", low_open_blocks.iloc[index % len(low_open_blocks)], rng, 90, 500))
        index += 1
    return records


def _added_transit_facilities(current: RenewalCurrentData, parameters: ScenarioParameterValues, rng: np.random.Generator) -> list[dict[str, Any]]:
    blocks = current.blocks.sort_values(["floor_area_ratio", "area_m2"], ascending=[False, False]).reset_index(drop=True)
    records: list[dict[str, Any]] = []
    index = 0
    for _ in range(parameters.new_bus_stops):
        records.append(_new_facility_record("C", index, "bus_stop", blocks.iloc[index % len(blocks)], rng, 180, 300))
        index += 1
    for _ in range(parameters.new_bike_stations):
        records.append(_new_facility_record("C", index, "bike_station", blocks.iloc[index % len(blocks)], rng, 70, 250))
        index += 1
    if parameters.shared_parking_spaces > 0:
        records.append(_new_facility_record("C", index, "shared_parking", blocks.iloc[index % len(blocks)], rng, parameters.shared_parking_spaces, 260))
    return records


def _new_facility_record(
    scenario_id: ScenarioId,
    index: int,
    facility_type: str,
    block: Any,
    rng: np.random.Generator,
    capacity: int,
    service_radius_m: int,
) -> dict[str, Any]:
    return {
        "facility_id": f"R01-S{scenario_id}-FAC-{index + 1:02d}",
        "geometry": _to_wgs84_geometry(_point_inside(block.geometry, rng)),
        "facility_type": facility_type,
        "capacity": int(capacity),
        "service_radius_m": int(service_radius_m),
        "change_type": "added",
    }


def _target_blocks_from_removed_buildings(current: RenewalCurrentData, removed_building_ids: list[str], count: int) -> gpd.GeoDataFrame:
    if count <= 0:
        return current.blocks.head(1)
    removed = current.buildings[current.buildings["building_id"].isin(removed_building_ids)]
    block_ids = removed["block_id"].drop_duplicates().tolist()
    blocks = current.blocks[current.blocks["block_id"].isin(block_ids)].sort_values("old_intensity", ascending=False)
    if len(blocks) >= count:
        return blocks.reset_index(drop=True)
    fallback = current.blocks.sort_values("old_intensity", ascending=False)
    return fallback.head(max(count, 1)).reset_index(drop=True)


def _new_building_geometry(block_geometry: Polygon, index: int, rng: np.random.Generator) -> Polygon:
    min_x, min_y, max_x, max_y = block_geometry.bounds
    width = min(72.0, max(46.0, (max_x - min_x) * 0.22))
    depth = min(58.0, max(36.0, (max_y - min_y) * 0.18))
    offsets = [(-0.22, -0.18), (0.18, -0.15), (-0.18, 0.16), (0.2, 0.18), (0.0, 0.0)]
    offset = offsets[index % len(offsets)]
    center_x = block_geometry.centroid.x + offset[0] * (max_x - min_x) + rng.normal(0, 8)
    center_y = block_geometry.centroid.y + offset[1] * (max_y - min_y) + rng.normal(0, 8)
    footprint = box(center_x - width / 2, center_y - depth / 2, center_x + width / 2, center_y + depth / 2)
    inner_block = block_geometry.buffer(-12)
    if not inner_block.is_empty and not inner_block.contains(footprint):
        footprint = footprint.intersection(inner_block)
    if footprint.is_empty or not isinstance(footprint, Polygon) or footprint.area < 200:
        fallback = block_geometry.representative_point()
        footprint = box(fallback.x - width / 2, fallback.y - depth / 2, fallback.x + width / 2, fallback.y + depth / 2).intersection(block_geometry.buffer(-8))
    if not isinstance(footprint, Polygon):
        footprint = footprint.convex_hull
    return footprint


def _point_inside(block_geometry: Polygon, rng: np.random.Generator) -> Point:
    min_x, min_y, max_x, max_y = block_geometry.bounds
    for _ in range(80):
        point = Point(rng.uniform(min_x + 32, max_x - 32), rng.uniform(min_y + 32, max_y - 32))
        if block_geometry.contains(point):
            return point
    return block_geometry.representative_point()


def _to_wgs84_geometry(geometry: BaseGeometry) -> dict[str, Any]:
    output = gpd.GeoSeries([geometry], crs=GRID_CRS).to_crs(BASE_CRS).iloc[0]
    return mapping(output)


def _scenario_seed(seed: int, scenario_id: ScenarioId, parameters: ScenarioParameterValues) -> int:
    parameter_hash = sum(int(float(value) * 100) for value in parameters.model_dump().values())
    scenario_offset = {"0": 0, "A": 101, "B": 211, "C": 307}[scenario_id]
    return int(seed * 1009 + scenario_offset + parameter_hash)


def _deterministic_created_at(seed: int, scenario_id: ScenarioId, parameters: ScenarioParameterValues) -> str:
    minute = _scenario_seed(seed, scenario_id, parameters) % 1440
    hour = minute // 60
    minute_of_hour = minute % 60
    return f"2026-07-14T{hour:02d}:{minute_of_hour:02d}:00+08:00"


def _road_type(width: float) -> str:
    if width < 5.0:
        return "alley"
    if width < 8.0:
        return "local"
    if width < 11.5:
        return "collector"
    return "arterial"


def _json_ready(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, ensure_ascii=False))
