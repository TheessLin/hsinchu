from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from app.grids import BASE_CRS, GRID_CRS
from app.phase2 import SYNTHETIC_DATA_DISCLAIMER
from app.renewal_current import R01_CANDIDATE_ID, RenewalCurrentData, get_r01_current_data
from app.renewal_scenarios import get_r01_scenario, normalize_scenario_id

KPI_IDS = [
    "residential_units",
    "resident_population",
    "daytime_population",
    "parking_supply",
    "parking_demand",
    "parking_gap",
    "park_area_m2",
    "park_service_population",
    "green_ratio",
    "open_space_ratio",
    "bus_access_score",
    "bike_access_score",
    "walkability_score",
    "shelter_service_population",
    "emergency_access_score",
    "commercial_activity_score",
    "resilience_score",
    "renewal_opportunity_score",
]


@dataclass(frozen=True)
class FormulaValue:
    value: float | None
    reason: str | None = None


@dataclass(frozen=True)
class AppliedScenarioData:
    scenario: dict[str, Any]
    current: RenewalCurrentData
    buildings: gpd.GeoDataFrame
    roads: gpd.GeoDataFrame
    facilities: gpd.GeoDataFrame
    land_area_m2: float

    @property
    def scenario_id(self) -> str:
        return str(self.scenario["scenario_id"])


@dataclass(frozen=True)
class KpiDefinition:
    kpi_id: str
    name: str
    unit: str
    formula_reference: str
    confidence_level: str
    assumptions: list[str]
    calculator: Callable[[AppliedScenarioData, dict[str, FormulaValue]], FormulaValue]


def get_r01_scenario_kpis(scenario_id: str) -> dict[str, Any] | None:
    normalized = normalize_scenario_id(scenario_id)
    if normalized is None:
        return None

    scenario = get_r01_scenario(normalized)
    if scenario is None:
        return None

    return build_r01_scenario_kpis(scenario)


def build_r01_scenario_kpis(scenario: dict[str, Any]) -> dict[str, Any] | None:
    baseline_scenario = get_r01_scenario("0")
    if baseline_scenario is None:
        return None

    current = get_r01_current_data()
    baseline_applied = apply_scenario(current, baseline_scenario)
    scenario_applied = apply_scenario(current, scenario)
    baseline_values = calculate_raw_kpis(baseline_applied)
    scenario_values = calculate_raw_kpis(scenario_applied, baseline_values)
    records = [
        _build_kpi_record(definition, scenario_values[definition.kpi_id], baseline_values[definition.kpi_id])
        for definition in KPI_DEFINITIONS
    ]
    return {
        "candidate_id": R01_CANDIDATE_ID,
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["scenario_name"],
        "baseline_scenario_id": "0",
        "data_type": "synthetic",
        "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
        "count": len(records),
        "kpis": {record["kpi_id"]: record for record in records},
        "records": records,
    }


def get_r01_scenario_comparison() -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    for scenario_id in ["0", "A", "B", "C"]:
        payload = get_r01_scenario_kpis(scenario_id)
        if payload is None:
            continue
        scenarios.append(
            {
                "scenario_id": payload["scenario_id"],
                "scenario_name": payload["scenario_name"],
                "kpis": payload["kpis"],
                "records": payload["records"],
            }
        )

    return {
        "candidate_id": R01_CANDIDATE_ID,
        "baseline_scenario_id": "0",
        "data_type": "synthetic",
        "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
        "count": len(scenarios),
        "scenarios": scenarios,
    }


def apply_scenario(current: RenewalCurrentData, scenario: dict[str, Any]) -> AppliedScenarioData:
    removed_ids = set(str(building_id) for building_id in scenario["removed_building_ids"])
    buildings = current.buildings[~current.buildings["building_id"].isin(removed_ids)].copy()
    if scenario["added_buildings"]:
        buildings = pd.concat([buildings, _records_to_frame(scenario["added_buildings"])], ignore_index=True)
        buildings = gpd.GeoDataFrame(buildings, geometry="geometry", crs=GRID_CRS)

    roads = current.roads.copy()
    if scenario["modified_roads"]:
        roads = roads.set_index("road_id", drop=False)
        for record in scenario["modified_roads"]:
            road_id = str(record["road_id"])
            if road_id not in roads.index:
                continue
            for field in ["width_m", "road_type", "sidewalk_width_m", "emergency_accessible", "pedestrian_capacity"]:
                roads.at[road_id, field] = record[field]
            roads.at[road_id, "geometry"] = _shape_to_grid(record["geometry"])
        roads = gpd.GeoDataFrame(roads.reset_index(drop=True), geometry="geometry", crs=GRID_CRS)

    facilities = current.facilities.copy()
    if scenario["added_facilities"]:
        facilities = pd.concat([facilities, _records_to_frame(scenario["added_facilities"])], ignore_index=True)
        facilities = gpd.GeoDataFrame(facilities, geometry="geometry", crs=GRID_CRS)

    return AppliedScenarioData(
        scenario=scenario,
        current=current,
        buildings=gpd.GeoDataFrame(buildings, geometry="geometry", crs=GRID_CRS),
        roads=gpd.GeoDataFrame(roads, geometry="geometry", crs=GRID_CRS),
        facilities=gpd.GeoDataFrame(facilities, geometry="geometry", crs=GRID_CRS),
        land_area_m2=float(current.blocks.geometry.union_all().area),
    )


def calculate_raw_kpis(
    data: AppliedScenarioData,
    baseline_values: dict[str, FormulaValue] | None = None,
) -> dict[str, FormulaValue]:
    values: dict[str, FormulaValue] = {}
    for definition in KPI_DEFINITIONS:
        if definition.kpi_id == "renewal_opportunity_score":
            values[definition.kpi_id] = calculate_renewal_opportunity_score(data, values, baseline_values)
        else:
            values[definition.kpi_id] = definition.calculator(data, values)
    return values


def calculate_residential_units(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    return FormulaValue(float(_sum_numeric(data.buildings, "residential_units")))


def calculate_resident_population(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    return FormulaValue(float(_sum_numeric(data.buildings, "estimated_population")))


def calculate_daytime_population(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    if len(data.buildings) == 0:
        return FormulaValue(None, "No buildings are available for daytime population calculation.")
    daytime = 0.0
    for _, building in data.buildings.iterrows():
        provided = building.get("daytime_population")
        if pd.notna(provided):
            daytime += float(provided)
        else:
            daytime += float(building.get("estimated_population", 0)) * 0.45
            daytime += float(building.get("commercial_floor_area", 0)) / 18
    return FormulaValue(round(daytime, 2))


def calculate_parking_supply(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    building_spaces = _sum_numeric(data.buildings, "parking_spaces")
    parking_facilities = data.facilities[data.facilities["facility_type"].isin(["parking", "underground_parking", "shared_parking"])]
    return FormulaValue(float(building_spaces + _sum_numeric(parking_facilities, "capacity")))


def calculate_parking_demand(data: AppliedScenarioData, values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    units = (values or {}).get("residential_units", calculate_residential_units(data)).value
    if units is None:
        return FormulaValue(None, "Residential units are unavailable for parking demand calculation.")
    commercial_floor_area = _sum_numeric(data.buildings, "commercial_floor_area")
    return FormulaValue(round(float(units) * 0.8 + commercial_floor_area / 80, 2))


def calculate_parking_gap(data: AppliedScenarioData, values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    supply = (values or {}).get("parking_supply", calculate_parking_supply(data)).value
    demand = (values or {}).get("parking_demand", calculate_parking_demand(data)).value
    if supply is None or demand is None:
        return FormulaValue(None, "Parking supply or demand is unavailable.")
    return FormulaValue(round(float(supply) - float(demand), 2))


def calculate_park_area_m2(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    if len(data.facilities) == 0:
        return FormulaValue(0.0)
    return FormulaValue(round(sum(_facility_area_proxy(row) for _, row in data.facilities.iterrows()), 2))


def calculate_park_service_population(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    return _served_population(data, ["park", "open_space", "disaster_plaza"], cap_by_capacity=False)


def calculate_green_ratio(data: AppliedScenarioData, values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    if data.land_area_m2 <= 0:
        return FormulaValue(None, "R-01 land area is zero; green ratio cannot be calculated.")
    block_green_area = float((data.current.blocks["area_m2"] * data.current.blocks["open_space_ratio"] * 0.35).sum())
    facility_green_area = 0.0
    for _, facility in data.facilities.iterrows():
        area = _facility_area_proxy(facility)
        facility_type = str(facility.get("facility_type"))
        multiplier = 1.0 if facility_type == "park" else 0.45 if facility_type == "disaster_plaza" else 0.35
        facility_green_area += area * multiplier
    ratio = (block_green_area + facility_green_area) / data.land_area_m2
    parameters = data.scenario.get("parameter_values", {})
    if data.scenario_id == "B" and data.scenario.get("added_facilities"):
        ratio = max(ratio, float(parameters.get("green_coverage_target", ratio)))
    return FormulaValue(round(_bounded(ratio, 0, 1), 4))


def calculate_open_space_ratio(data: AppliedScenarioData, values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    if data.land_area_m2 <= 0:
        return FormulaValue(None, "R-01 land area is zero; open-space ratio cannot be calculated.")
    base_open_area = float((data.current.blocks["area_m2"] * data.current.blocks["open_space_ratio"]).sum())
    added_open_area = sum(_facility_area_proxy(row) for _, row in data.facilities.iterrows() if str(row.get("facility_type")) in {"park", "open_space", "disaster_plaza"})
    ratio = (base_open_area + added_open_area) / data.land_area_m2
    parameters = data.scenario.get("parameter_values", {})
    if data.scenario_id == "A" and data.scenario.get("added_facilities"):
        ratio = max(ratio, float(parameters.get("minimum_open_space_ratio", ratio)))
    return FormulaValue(round(_bounded(ratio, 0, 1), 4))


def calculate_bus_access_score(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    return _facility_access_score(data, ["bus_stop"], "bus access score")


def calculate_bike_access_score(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    return _facility_access_score(data, ["bike_station"], "bike access score")


def calculate_walkability_score(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    if len(data.roads) == 0:
        return FormulaValue(None, "No roads are available for walkability calculation.")
    sidewalk_score = _bounded(float(data.roads["sidewalk_width_m"].mean()) / 3.0 * 100, 0, 100)
    capacity_score = _bounded(float(data.roads["pedestrian_capacity"].mean()) / 900 * 100, 0, 100)
    local_connectivity = _bounded(len(data.roads) / max(data.land_area_m2 / 100000, 1) * 12, 0, 100)
    score = 0.45 * sidewalk_score + 0.30 * capacity_score + 0.25 * local_connectivity
    return FormulaValue(round(score, 2))


def calculate_shelter_service_population(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    return _served_population(data, ["shelter", "disaster_plaza"], cap_by_capacity=True)


def calculate_emergency_access_score(data: AppliedScenarioData, _values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    if len(data.roads) == 0:
        return FormulaValue(None, "No roads are available for emergency access calculation.")
    total_length = float(data.roads.geometry.length.sum())
    if total_length <= 0:
        return FormulaValue(None, "Total road length is zero; emergency access cannot be calculated.")
    accessible = data.roads[data.roads["emergency_accessible"] == True]  # noqa: E712
    accessible_ratio = float(accessible.geometry.length.sum()) / total_length
    width_score = _bounded(float(data.roads["width_m"].mean()) / 8.0 * 100, 0, 100)
    score = 0.65 * accessible_ratio * 100 + 0.35 * width_score
    return FormulaValue(round(_bounded(score, 0, 100), 2))


def calculate_commercial_activity_score(data: AppliedScenarioData, values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    commercial_floor_area = _sum_numeric(data.buildings, "commercial_floor_area")
    daytime = (values or {}).get("daytime_population", calculate_daytime_population(data)).value
    if daytime is None:
        return FormulaValue(None, "Daytime population is unavailable for commercial activity calculation.")
    mixed_use_ratio = 0.0 if len(data.buildings) == 0 else float((data.buildings["use_type"] == "mixed_use").mean())
    commercial_score = _bounded(commercial_floor_area / 350000 * 100, 0, 100)
    daytime_score = _bounded(float(daytime) / 35000 * 100, 0, 100)
    score = 0.42 * commercial_score + 0.38 * daytime_score + 0.20 * mixed_use_ratio * 100
    return FormulaValue(round(_bounded(score, 0, 100), 2))


def calculate_resilience_score(data: AppliedScenarioData, values: dict[str, FormulaValue] | None = None) -> FormulaValue:
    values = values or {}
    required = [
        "green_ratio",
        "open_space_ratio",
        "bus_access_score",
        "bike_access_score",
        "walkability_score",
        "shelter_service_population",
        "park_service_population",
        "emergency_access_score",
        "resident_population",
    ]
    missing = [key for key in required if key not in values or values[key].value is None]
    if missing:
        return FormulaValue(None, f"Required KPI values are unavailable: {', '.join(missing)}.")
    resident_population = max(float(values["resident_population"].value or 0), 0)
    if resident_population <= 0:
        return FormulaValue(None, "Resident population is zero; resilience score cannot be calculated.")
    park_coverage = _bounded(float(values["park_service_population"].value or 0) / resident_population * 100, 0, 100)
    shelter_coverage = _bounded(float(values["shelter_service_population"].value or 0) / resident_population * 100, 0, 100)
    old_ratio = _old_building_ratio(data)
    built_environment = _bounded(100 - old_ratio * 55 + float(values["open_space_ratio"].value or 0) * 18, 0, 100)
    hazard_evacuation = _bounded(0.62 * float(values["emergency_access_score"].value or 0) + 0.38 * shelter_coverage, 0, 100)
    transport = _average_values([values["bus_access_score"].value, values["bike_access_score"].value, values["walkability_score"].value])
    social = _bounded(54 + shelter_coverage * 0.22 + park_coverage * 0.14, 0, 100)
    living_health = _bounded(0.35 * park_coverage + 0.35 * float(values["green_ratio"].value or 0) * 100 + 0.30 * float(values["open_space_ratio"].value or 0) * 100, 0, 100)
    renewal_health = _bounded(100 - old_ratio * 100, 0, 100)
    score = (
        built_environment * 0.25
        + hazard_evacuation * 0.20
        + transport * 0.15
        + social * 0.15
        + living_health * 0.15
        + renewal_health * 0.10
    )
    return FormulaValue(round(_bounded(score, 0, 100), 2))


def calculate_renewal_opportunity_score(
    data: AppliedScenarioData,
    values: dict[str, FormulaValue] | None = None,
    baseline_values: dict[str, FormulaValue] | None = None,
) -> FormulaValue:
    priority_count = int((data.current.buildings["renewal_status"] == "priority").sum())
    monitor_count = int((data.current.buildings["renewal_status"] == "monitor").sum())
    total_current = max(len(data.current.buildings), 1)
    existing_condition_deficit = _bounded((priority_count * 1.0 + monitor_count * 0.45) / total_current * 100, 0, 100)
    removed_count = len(data.scenario.get("removed_building_ids", []))
    land_reconfiguration = _bounded(removed_count / max(priority_count, 1) * 100, 0, 100)
    infrastructure_gain = _bounded(len(data.scenario.get("modified_roads", [])) * 12 + len(data.scenario.get("added_facilities", [])) * 6, 0, 100)
    strategic_location = _bounded(((values or {}).get("bus_access_score", FormulaValue(0)).value or 0) * 0.55 + ((values or {}).get("commercial_activity_score", FormulaValue(0)).value or 0) * 0.45, 0, 100)
    baseline_resilience = (baseline_values or {}).get("resilience_score", FormulaValue(None)).value
    current_resilience = (values or {}).get("resilience_score", FormulaValue(None)).value
    if baseline_resilience is None or current_resilience is None:
        scenario_gain = 0.0
    else:
        scenario_gain = _bounded((float(current_resilience) - float(baseline_resilience)) * 3, 0, 100)
    score = (
        0.30 * existing_condition_deficit
        + 0.20 * scenario_gain
        + 0.15 * land_reconfiguration
        + 0.15 * infrastructure_gain
        + 0.10 * strategic_location
        + 0.10 * _bounded(removed_count * 10, 0, 100)
    )
    return FormulaValue(round(_bounded(score, 0, 100), 2))


def calculate_percentage_change(value: float | None, baseline_value: float | None) -> FormulaValue:
    if value is None or baseline_value is None:
        return FormulaValue(None, "Value or baseline_value is null; percentage_change cannot be calculated.")
    if baseline_value == 0:
        return FormulaValue(None, "baseline_value is zero; percentage_change cannot be calculated.")
    return FormulaValue(round((float(value) - float(baseline_value)) / abs(float(baseline_value)) * 100, 2))


def _build_kpi_record(definition: KpiDefinition, current: FormulaValue, baseline: FormulaValue) -> dict[str, Any]:
    percentage = calculate_percentage_change(current.value, baseline.value)
    absolute_change = None
    if current.value is not None and baseline.value is not None:
        absolute_change = round(float(current.value) - float(baseline.value), 4)
    reasons = [reason for reason in [current.reason, baseline.reason, percentage.reason] if reason]
    return {
        "kpi_id": definition.kpi_id,
        "name": definition.name,
        "value": _round_kpi_value(current.value),
        "unit": definition.unit,
        "baseline_value": _round_kpi_value(baseline.value),
        "absolute_change": absolute_change,
        "percentage_change": percentage.value,
        "formula_reference": definition.formula_reference,
        "confidence_level": definition.confidence_level,
        "assumptions": definition.assumptions,
        "reason": "; ".join(dict.fromkeys(reasons)) if reasons else None,
    }


def _records_to_frame(records: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        row = {key: value for key, value in record.items() if key != "geometry"}
        row["geometry"] = _shape_to_grid(record["geometry"])
        rows.append(row)
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=GRID_CRS)


def _shape_to_grid(geometry: dict[str, Any]) -> Any:
    return gpd.GeoSeries([shape(geometry)], crs=BASE_CRS).to_crs(GRID_CRS).iloc[0]


def _sum_numeric(frame: pd.DataFrame, field: str) -> float:
    if field not in frame.columns:
        return 0.0
    return float(pd.to_numeric(frame[field], errors="coerce").fillna(0).sum())


def _facility_area_proxy(row: Any) -> float:
    facility_type = str(row.get("facility_type"))
    capacity = max(float(row.get("capacity", 0) or 0), 0)
    multipliers = {
        "park": 2.5,
        "open_space": 2.2,
        "disaster_plaza": 2.8,
        "shelter": 1.2,
        "underground_parking": 0.0,
        "shared_parking": 0.0,
        "parking": 0.0,
    }
    return capacity * multipliers.get(facility_type, 0.45)


def _served_population(data: AppliedScenarioData, facility_types: list[str], cap_by_capacity: bool) -> FormulaValue:
    if len(data.buildings) == 0:
        return FormulaValue(None, "No buildings are available for service population calculation.")
    facilities = data.facilities[data.facilities["facility_type"].isin(facility_types)]
    if len(facilities) == 0:
        return FormulaValue(0.0)
    served = 0.0
    for _, building in data.buildings.iterrows():
        centroid = building.geometry.centroid
        population = float(building.get("estimated_population", 0) or 0)
        if any(centroid.distance(facility.geometry) <= float(facility.get("service_radius_m", 0) or 0) for _, facility in facilities.iterrows()):
            served += population
    if cap_by_capacity:
        served = min(served, _sum_numeric(facilities, "capacity"))
    return FormulaValue(round(served, 2))


def _facility_access_score(data: AppliedScenarioData, facility_types: list[str], label: str) -> FormulaValue:
    population = calculate_resident_population(data).value
    if population is None or population <= 0:
        return FormulaValue(None, f"Resident population is zero; {label} cannot be calculated.")
    facilities = data.facilities[data.facilities["facility_type"].isin(facility_types)]
    if len(facilities) == 0:
        return FormulaValue(0.0)
    served = _served_population(data, facility_types, cap_by_capacity=False)
    if served.value is None:
        return FormulaValue(None, served.reason)
    served_score = _bounded(float(served.value) / float(population) * 100, 0, 100)
    density_score = _bounded(len(facilities) / max(data.land_area_m2 / 100000, 1) * 18, 0, 100)
    return FormulaValue(round(0.76 * served_score + 0.24 * density_score, 2))


def _old_building_ratio(data: AppliedScenarioData) -> float:
    if len(data.buildings) == 0 or "age" not in data.buildings.columns:
        return 0.0
    ages = pd.to_numeric(data.buildings["age"], errors="coerce").fillna(0)
    return float((ages >= 35).mean())


def _average_values(values: list[float | None]) -> float:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return 0.0
    return sum(numeric) / len(numeric)


def _round_kpi_value(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _bounded(value: float, lower: float, upper: float) -> float:
    return min(max(float(value), lower), upper)


KPI_DEFINITIONS = [
    KpiDefinition(
        "residential_units",
        "住宅戶數",
        "戶",
        "sum(building.residential_units)",
        "high",
        ["新增建物戶數由 Scenario Engine 依樓層與每層戶數推估。"],
        calculate_residential_units,
    ),
    KpiDefinition(
        "resident_population",
        "居住人口",
        "人",
        "sum(building.estimated_population)",
        "high",
        ["居住人口為合成建物戶數乘以每戶人口假設。"],
        calculate_resident_population,
    ),
    KpiDefinition(
        "daytime_population",
        "日間人口",
        "人",
        "residents * 0.45 + commercial_floor_area / 18 + scenario daytime additions",
        "medium",
        ["現況日間人口使用住宅留置率與商業樓地板就業人口 proxy。"],
        calculate_daytime_population,
    ),
    KpiDefinition(
        "parking_supply",
        "停車供給",
        "席",
        "building.parking_spaces + parking facility capacity",
        "medium",
        ["點狀停車設施以 capacity 表示可供給車位。"],
        calculate_parking_supply,
    ),
    KpiDefinition(
        "parking_demand",
        "停車需求",
        "席",
        "residential_units * 0.8 + commercial_floor_area / 80",
        "medium",
        ["商業停車需求使用樓地板面積除以 80 平方公尺的 proxy。"],
        calculate_parking_demand,
    ),
    KpiDefinition("parking_gap", "停車缺口", "席", "parking_supply - parking_demand", "medium", ["正值表示供給大於需求。"], calculate_parking_gap),
    KpiDefinition(
        "park_area_m2",
        "公園開放空間面積",
        "m2",
        "sum(facility.capacity * facility_type_area_multiplier)",
        "low",
        ["現況設施為點資料，公園及開放空間面積以容量乘上類型係數推估。"],
        calculate_park_area_m2,
    ),
    KpiDefinition(
        "park_service_population",
        "公園服務人口",
        "人",
        "sum(building.population within park service radius)",
        "medium",
        ["服務人口以建物中心點是否落入服務半徑判定。"],
        calculate_park_service_population,
    ),
    KpiDefinition(
        "green_ratio",
        "綠覆率",
        "比例",
        "(block green proxy + facility green proxy) / R-01 land area",
        "low",
        ["Scenario B 的綠覆率納入後端參數化設計目標作為下限。"],
        calculate_green_ratio,
    ),
    KpiDefinition(
        "open_space_ratio",
        "開放空間率",
        "比例",
        "(block open-space proxy + added open-space proxy) / R-01 land area",
        "low",
        ["Scenario A 的基本開放空間以後端參數化設計目標作為下限。"],
        calculate_open_space_ratio,
    ),
    KpiDefinition("bus_access_score", "公車可及性", "分", "population weighted bus stop service coverage", "medium", ["服務半徑使用設施資料欄位。"], calculate_bus_access_score),
    KpiDefinition("bike_access_score", "自行車可及性", "分", "population weighted bike station service coverage", "medium", ["服務半徑使用設施資料欄位。"], calculate_bike_access_score),
    KpiDefinition("walkability_score", "步行友善度", "分", "0.45 sidewalk + 0.30 capacity + 0.25 connectivity", "medium", ["道路連通性為小範圍道路密度 proxy。"], calculate_walkability_score),
    KpiDefinition(
        "shelter_service_population",
        "避難服務人口",
        "人",
        "min(population within shelter radius, shelter capacity)",
        "medium",
        ["避難廣場以 shelter 類型共同納入服務容量。"],
        calculate_shelter_service_population,
    ),
    KpiDefinition("emergency_access_score", "消防救災可及性", "分", "0.65 accessible road ratio + 0.35 road width score", "medium", ["可通行道路由 emergency_accessible 欄位判定。"], calculate_emergency_access_score),
    KpiDefinition("commercial_activity_score", "商業活動分數", "分", "commercial floor area + daytime population + mixed-use ratio", "medium", ["商業活動為合成資料 proxy，不代表實際營業狀態。"], calculate_commercial_activity_score),
    KpiDefinition(
        "resilience_score",
        "都市韌性健康度",
        "分",
        "0.25 BE + 0.20 HE + 0.15 TA + 0.15 SD + 0.15 LH + 0.10 RP",
        "medium",
        ["小範圍韌性分數由本模組 KPI 重組，並非第一階段官方政策結論。"],
        calculate_resilience_score,
    ),
    KpiDefinition(
        "renewal_opportunity_score",
        "更新機會分數",
        "分",
        "condition deficit + scenario gain + land reconfiguration + infrastructure gain + strategic location",
        "low",
        ["高分代表更新模擬機會較高，不代表真實都市更新優先順序。"],
        lambda data, values: calculate_renewal_opportunity_score(data, values),
    ),
]
