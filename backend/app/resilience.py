from typing import Any

import pandas as pd

from app.simulation import FIELD_RANGES, get_simulation_grid, get_simulation_state

DIMENSION_WEIGHTS: dict[str, float] = {
    "built_environment_score": 0.25,
    "disaster_evacuation_score": 0.20,
    "transport_access_score": 0.15,
    "social_demographic_score": 0.15,
    "living_health_score": 0.15,
    "renewal_potential_score": 0.10,
}


def get_resilience_records() -> list[dict[str, Any]]:
    state = get_simulation_state()
    return [calculate_resilience_record(record) for record in state.frame.to_dict(orient="records")]


def get_resilience_grid(grid_id: str) -> dict[str, Any] | None:
    record = get_simulation_grid(grid_id)
    if record is None:
        return None

    return calculate_resilience_record(record)


def calculate_resilience_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame.from_records([calculate_resilience_record(record) for record in frame.to_dict(orient="records")])


def calculate_resilience_record(record: dict[str, Any]) -> dict[str, Any]:
    built_environment = _built_environment(record)
    disaster_evacuation = _disaster_evacuation(record)
    transport_access = _transport_access(record)
    social_demographic = _social_demographic(record)
    living_health = _living_health(record)
    renewal_potential = _renewal_potential(record)

    dimension_scores = {
        "built_environment_score": built_environment["score"],
        "disaster_evacuation_score": disaster_evacuation["score"],
        "transport_access_score": transport_access["score"],
        "social_demographic_score": social_demographic["score"],
        "living_health_score": living_health["score"],
        "renewal_potential_score": renewal_potential["score"],
    }
    resilience_score = round(
        sum(dimension_scores[name] * weight for name, weight in DIMENSION_WEIGHTS.items()),
        2,
    )

    return {
        **record,
        **dimension_scores,
        "resilience_score": resilience_score,
        "score_details": {
            "built_environment_score": built_environment,
            "disaster_evacuation_score": disaster_evacuation,
            "transport_access_score": transport_access,
            "social_demographic_score": social_demographic,
            "living_health_score": living_health,
            "renewal_potential_score": renewal_potential,
        },
    }


def _built_environment(record: dict[str, Any]) -> dict[str, Any]:
    components = {
        "building_age_condition": _negative(record["average_building_age"], "average_building_age"),
        "old_building_condition": _negative(record["old_building_ratio"], "old_building_ratio"),
        "coverage_condition": _negative(record["building_coverage_ratio"], "building_coverage_ratio"),
        "density_condition": _negative(record["building_count"], "building_count"),
    }
    weights = {
        "building_age_condition": 0.30,
        "old_building_condition": 0.30,
        "coverage_condition": 0.25,
        "density_condition": 0.15,
    }
    return _dimension_result(components, weights)


def _disaster_evacuation(record: dict[str, Any]) -> dict[str, Any]:
    components = {
        "shelter_access": _positive(record["shelter_access_score"], "shelter_access_score"),
        "fire_safety": _negative(record["fire_risk"], "fire_risk"),
        "flood_safety": _negative(record["flood_risk"], "flood_risk"),
        "road_evacuation_condition": _negative(record["narrow_road_ratio"], "narrow_road_ratio"),
        "open_space_support": _positive(record["open_space_ratio"], "open_space_ratio"),
    }
    weights = {
        "shelter_access": 0.25,
        "fire_safety": 0.25,
        "flood_safety": 0.20,
        "road_evacuation_condition": 0.20,
        "open_space_support": 0.10,
    }
    return _dimension_result(components, weights)


def _transport_access(record: dict[str, Any]) -> dict[str, Any]:
    components = {
        "bus_access": _positive(record["bus_access_score"], "bus_access_score"),
        "bike_access": _positive(record["bike_access_score"], "bike_access_score"),
        "walkability": _positive(record["walkability_score"], "walkability_score"),
        "parking_adequacy": _parking_adequacy(record["parking_supply"], record["parking_demand"]),
    }
    weights = {
        "bus_access": 0.35,
        "bike_access": 0.20,
        "walkability": 0.30,
        "parking_adequacy": 0.15,
    }
    return _dimension_result(components, weights)


def _social_demographic(record: dict[str, Any]) -> dict[str, Any]:
    components = {
        "elderly_vulnerability": _negative(record["elderly_ratio"], "elderly_ratio"),
        "child_service_balance": _target_score(record["child_ratio"], target=0.14, tolerance=0.09),
        "residential_pressure": _negative(record["population"], "population"),
        "daytime_pressure": _negative(record["daytime_population"], "daytime_population"),
    }
    weights = {
        "elderly_vulnerability": 0.35,
        "child_service_balance": 0.20,
        "residential_pressure": 0.25,
        "daytime_pressure": 0.20,
    }
    return _dimension_result(components, weights)


def _living_health(record: dict[str, Any]) -> dict[str, Any]:
    components = {
        "medical_access": _positive(record["medical_access_score"], "medical_access_score"),
        "park_access": _positive(record["park_access_score"], "park_access_score"),
        "green_environment": _positive(record["green_ratio"], "green_ratio"),
        "open_space_environment": _positive(record["open_space_ratio"], "open_space_ratio"),
        "daily_service_activity": _positive(record["commercial_activity"], "commercial_activity"),
    }
    weights = {
        "medical_access": 0.30,
        "park_access": 0.25,
        "green_environment": 0.20,
        "open_space_environment": 0.15,
        "daily_service_activity": 0.10,
    }
    return _dimension_result(components, weights)


def _renewal_potential(record: dict[str, Any]) -> dict[str, Any]:
    components = {
        "renewal_pressure_inverse": _negative(record["renewal_potential"], "renewal_potential"),
        "ownership_simplicity": _negative(record["ownership_complexity"], "ownership_complexity"),
        "old_building_inverse": _negative(record["old_building_ratio"], "old_building_ratio"),
    }
    weights = {
        "renewal_pressure_inverse": 0.60,
        "ownership_simplicity": 0.25,
        "old_building_inverse": 0.15,
    }
    result = _dimension_result(components, weights)
    result["raw_renewal_potential"] = round(float(record["renewal_potential"]), 2)
    return result


def _dimension_result(components: dict[str, float], weights: dict[str, float]) -> dict[str, Any]:
    score = round(sum(components[name] * weights[name] for name in weights), 2)
    return {
        "score": _clamp_score(score),
        "components": {name: round(value, 2) for name, value in components.items()},
        "weights": weights,
    }


def _positive(value: float, field: str) -> float:
    lower, upper = FIELD_RANGES[field]
    return _normalize(value, lower, upper)


def _negative(value: float, field: str) -> float:
    return 100 - _positive(value, field)


def _normalize(value: float, lower: float, upper: float) -> float:
    if upper == lower:
        return 50.0

    return _clamp_score(((float(value) - lower) / (upper - lower)) * 100)


def _target_score(value: float, target: float, tolerance: float) -> float:
    if tolerance <= 0:
        return 50.0

    distance = abs(float(value) - target)
    return _clamp_score(100 - (distance / tolerance) * 100)


def _parking_adequacy(parking_supply: float, parking_demand: float) -> float:
    if parking_demand <= 0:
        return 100.0

    return _clamp_score((float(parking_supply) / float(parking_demand)) * 100)


def _clamp_score(value: float) -> float:
    return round(min(max(float(value), 0), 100), 2)
