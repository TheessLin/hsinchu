from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.grids import GRID_CRS, generate_analysis_grids

DEFAULT_SIMULATION_SEED = 42
DEFAULT_SIMULATION_LEVEL = 50.0

SYNTHETIC_FIELDS = [
    "population",
    "daytime_population",
    "elderly_ratio",
    "child_ratio",
    "building_count",
    "average_building_age",
    "old_building_ratio",
    "building_coverage_ratio",
    "narrow_road_ratio",
    "open_space_ratio",
    "green_ratio",
    "parking_supply",
    "parking_demand",
    "bus_access_score",
    "bike_access_score",
    "walkability_score",
    "shelter_access_score",
    "fire_risk",
    "flood_risk",
    "medical_access_score",
    "park_access_score",
    "commercial_activity",
    "ownership_complexity",
    "renewal_potential",
]

FIELD_RANGES: dict[str, tuple[float, float]] = {
    "population": (30, 2400),
    "daytime_population": (20, 3200),
    "elderly_ratio": (0.06, 0.32),
    "child_ratio": (0.05, 0.22),
    "building_count": (1, 120),
    "average_building_age": (3, 60),
    "old_building_ratio": (0.02, 0.85),
    "building_coverage_ratio": (0.08, 0.82),
    "narrow_road_ratio": (0.05, 0.75),
    "open_space_ratio": (0.03, 0.65),
    "green_ratio": (0.02, 0.55),
    "parking_supply": (0, 900),
    "parking_demand": (0, 1400),
    "bus_access_score": (0, 100),
    "bike_access_score": (0, 100),
    "walkability_score": (0, 100),
    "shelter_access_score": (0, 100),
    "fire_risk": (0, 100),
    "flood_risk": (0, 100),
    "medical_access_score": (0, 100),
    "park_access_score": (0, 100),
    "commercial_activity": (0, 100),
    "ownership_complexity": (0, 100),
    "renewal_potential": (0, 100),
}


@dataclass(frozen=True)
class SimulationParameters:
    random_seed: int = DEFAULT_SIMULATION_SEED
    old_area_intensity: float = DEFAULT_SIMULATION_LEVEL
    population_density: float = DEFAULT_SIMULATION_LEVEL
    public_transport_level: float = DEFAULT_SIMULATION_LEVEL
    green_space_level: float = DEFAULT_SIMULATION_LEVEL
    disaster_risk_level: float = DEFAULT_SIMULATION_LEVEL

    def bounded(self) -> "SimulationParameters":
        return SimulationParameters(
            random_seed=int(self.random_seed),
            old_area_intensity=_clamp(self.old_area_intensity, 0, 100),
            population_density=_clamp(self.population_density, 0, 100),
            public_transport_level=_clamp(self.public_transport_level, 0, 100),
            green_space_level=_clamp(self.green_space_level, 0, 100),
            disaster_risk_level=_clamp(self.disaster_risk_level, 0, 100),
        )

    def as_dict(self) -> dict[str, float | int]:
        return {
            "random_seed": self.random_seed,
            "old_area_intensity": self.old_area_intensity,
            "population_density": self.population_density,
            "public_transport_level": self.public_transport_level,
            "green_space_level": self.green_space_level,
            "disaster_risk_level": self.disaster_risk_level,
        }


@dataclass
class SimulationState:
    seed: int
    parameters: SimulationParameters
    frame: pd.DataFrame


_simulation_state: SimulationState | None = None


def generate_synthetic_data(
    seed: int = DEFAULT_SIMULATION_SEED,
    old_area_intensity: float = DEFAULT_SIMULATION_LEVEL,
    population_density: float = DEFAULT_SIMULATION_LEVEL,
    public_transport_level: float = DEFAULT_SIMULATION_LEVEL,
    green_space_level: float = DEFAULT_SIMULATION_LEVEL,
    disaster_risk_level: float = DEFAULT_SIMULATION_LEVEL,
) -> pd.DataFrame:
    parameters = SimulationParameters(
        random_seed=seed,
        old_area_intensity=old_area_intensity,
        population_density=population_density,
        public_transport_level=public_transport_level,
        green_space_level=green_space_level,
        disaster_risk_level=disaster_risk_level,
    ).bounded()
    old_area_factor = _level_factor(parameters.old_area_intensity)
    population_factor = _level_factor(parameters.population_density)
    transport_factor = _level_factor(parameters.public_transport_level)
    green_factor = _level_factor(parameters.green_space_level)
    disaster_factor = _level_factor(parameters.disaster_risk_level)

    grids = generate_analysis_grids()
    projected_grids = grids.to_crs(GRID_CRS)
    center = projected_grids.geometry.union_all().centroid
    centroids = projected_grids.geometry.centroid
    distances = centroids.distance(center)
    max_distance = float(distances.max()) if float(distances.max()) > 0 else 1.0
    rng = np.random.default_rng(parameters.random_seed)

    records: list[dict[str, Any]] = []
    for index, grid in grids.reset_index(drop=True).iterrows():
        projected_centroid = centroids.iloc[index]
        distance_ratio = _clamp(float(distances.iloc[index]) / max_distance, 0, 1)
        core_intensity = 1 - distance_ratio
        edge_intensity = distance_ratio
        emerging_intensity = _emerging_residential_intensity(distance_ratio, projected_centroid.x, projected_centroid.y, center.x, center.y)
        southern_green_influence = 1.0 if projected_centroid.y < center.y - 3200 else 0.0
        eastern_service_influence = 1.0 if projected_centroid.x > center.x + 1200 else 0.0
        variation = rng.normal(0, 1, 24)

        population = _bounded_int(
            (
                170
                + 1500 * core_intensity
                + 520 * emerging_intensity
                - 260 * edge_intensity
                + 120 * eastern_service_influence
                + variation[0] * 75
            )
            * (1 + 0.45 * population_factor),
            "population",
        )
        commercial_activity = _bounded_score(
            12
            + 82 * core_intensity
            + 16 * eastern_service_influence
            - 20 * edge_intensity
            + variation[1] * 5,
            "commercial_activity",
        )
        daytime_population = _bounded_int(
            population * (0.75 + commercial_activity / 85) * (1 + 0.18 * population_factor)
            + 150 * eastern_service_influence
            + variation[2] * 90,
            "daytime_population",
        )
        average_building_age = _bounded_int(
            8
            + 38 * core_intensity
            - 12 * emerging_intensity
            + 10 * old_area_factor
            + variation[3] * 3.2,
            "average_building_age",
        )
        old_building_ratio = _bounded_ratio(
            0.05
            + 0.62 * core_intensity
            - 0.22 * emerging_intensity
            + 0.18 * old_area_factor
            + variation[4] * 0.035,
            "old_building_ratio",
        )
        building_count = _bounded_int(
            (10 + 82 * core_intensity + 24 * emerging_intensity - 12 * edge_intensity + variation[5] * 5)
            * (1 + 0.25 * population_factor + 0.12 * old_area_factor),
            "building_count",
        )
        building_coverage_ratio = _bounded_ratio(
            0.18
            + 0.48 * core_intensity
            + 0.12 * emerging_intensity
            - 0.08 * edge_intensity
            + 0.07 * population_factor
            + 0.05 * old_area_factor
            + variation[6] * 0.025,
            "building_coverage_ratio",
        )
        narrow_road_ratio = _bounded_ratio(
            0.12
            + 0.48 * core_intensity
            - 0.22 * emerging_intensity
            + 0.12 * old_area_factor
            - 0.04 * transport_factor
            + variation[7] * 0.035,
            "narrow_road_ratio",
        )
        open_space_ratio = _bounded_ratio(
            0.09
            + 0.28 * edge_intensity
            + 0.16 * emerging_intensity
            - 0.12 * core_intensity
            + 0.10 * green_factor
            - 0.06 * population_factor
            + variation[8] * 0.025,
            "open_space_ratio",
        )
        green_ratio = _bounded_ratio(
            0.06
            + 0.34 * edge_intensity
            + 0.16 * southern_green_influence
            - 0.12 * core_intensity
            + 0.16 * green_factor
            - 0.06 * population_factor
            + variation[9] * 0.025,
            "green_ratio",
        )
        parking_demand = _bounded_int(
            (95 + population * 0.42 + commercial_activity * 5.2 + 120 * core_intensity + variation[10] * 45)
            * (1 + 0.25 * population_factor),
            "parking_demand",
        )
        parking_supply = _bounded_int(
            70 + population * 0.16 + 340 * emerging_intensity + 150 * edge_intensity - 80 * core_intensity + variation[11] * 35,
            "parking_supply",
        )
        bus_access_score = _bounded_score(
            25
            + 62 * core_intensity
            + 18 * eastern_service_influence
            - 26 * edge_intensity
            + 24 * transport_factor
            + variation[12] * 4,
            "bus_access_score",
        )
        bike_access_score = _bounded_score(
            30
            + 38 * emerging_intensity
            + 26 * core_intensity
            - 10 * edge_intensity
            + 18 * transport_factor
            + variation[13] * 5,
            "bike_access_score",
        )
        walkability_score = _bounded_score(
            32
            + 42 * core_intensity
            + 25 * emerging_intensity
            - 18 * edge_intensity
            - 12 * narrow_road_ratio
            + 10 * transport_factor
            + variation[14] * 4,
            "walkability_score",
        )
        shelter_access_score = _bounded_score(
            28
            + 45 * core_intensity
            + 12 * open_space_ratio * 100 / 65
            - 14 * edge_intensity
            + 8 * green_factor
            - 8 * disaster_factor
            + variation[15] * 5,
            "shelter_access_score",
        )
        fire_risk = _bounded_score(
            10
            + old_building_ratio * 48
            + narrow_road_ratio * 36
            + building_coverage_ratio * 20
            - green_ratio * 18
            + 14 * disaster_factor
            + 10 * old_area_factor
            - 6 * green_factor
            + variation[16] * 4,
            "fire_risk",
        )
        flood_risk = _bounded_score(
            12
            + 22 * southern_green_influence
            + 14 * edge_intensity
            - open_space_ratio * 12
            + 16 * disaster_factor
            - 8 * green_factor
            + variation[17] * 5,
            "flood_risk",
        )
        medical_access_score = _bounded_score(
            30
            + 58 * core_intensity
            + 15 * eastern_service_influence
            - 24 * edge_intensity
            + 8 * transport_factor
            + variation[18] * 4,
            "medical_access_score",
        )
        park_access_score = _bounded_score(
            18
            + 58 * green_ratio
            + 34 * open_space_ratio
            + 8 * emerging_intensity
            - 10 * core_intensity
            + 18 * green_factor
            + variation[19] * 4,
            "park_access_score",
        )
        elderly_ratio = _bounded_ratio(
            0.09 + 0.13 * core_intensity + 0.04 * edge_intensity + variation[20] * 0.012,
            "elderly_ratio",
        )
        child_ratio = _bounded_ratio(
            0.08 + 0.08 * emerging_intensity + 0.03 * edge_intensity - 0.03 * core_intensity + variation[21] * 0.01,
            "child_ratio",
        )
        ownership_complexity = _bounded_score(
            18
            + 44 * old_building_ratio
            + 26 * core_intensity
            + 10 * building_coverage_ratio
            + 8 * old_area_factor
            + variation[22] * 4,
            "ownership_complexity",
        )
        renewal_potential = _bounded_score(
            0.28 * fire_risk
            + 0.2 * ownership_complexity
            + 0.18 * (old_building_ratio * 100)
            + 0.14 * (building_coverage_ratio * 100)
            + 0.12 * commercial_activity
            + 0.08 * (100 - green_ratio * 100)
            + 8 * old_area_factor
            + 5 * population_factor
            + 5 * disaster_factor
            - 5 * green_factor
            + variation[23] * 2.5,
            "renewal_potential",
        )

        records.append(
            {
                "grid_id": str(grid["grid_id"]),
                "centroid_x": float(grid["centroid_x"]),
                "centroid_y": float(grid["centroid_y"]),
                "district_type": str(grid["district_type"]),
                "land_use_type": str(grid["land_use_type"]),
                "population": population,
                "daytime_population": daytime_population,
                "elderly_ratio": elderly_ratio,
                "child_ratio": child_ratio,
                "building_count": building_count,
                "average_building_age": average_building_age,
                "old_building_ratio": old_building_ratio,
                "building_coverage_ratio": building_coverage_ratio,
                "narrow_road_ratio": narrow_road_ratio,
                "open_space_ratio": open_space_ratio,
                "green_ratio": green_ratio,
                "parking_supply": parking_supply,
                "parking_demand": parking_demand,
                "bus_access_score": bus_access_score,
                "bike_access_score": bike_access_score,
                "walkability_score": walkability_score,
                "shelter_access_score": shelter_access_score,
                "fire_risk": fire_risk,
                "flood_risk": flood_risk,
                "medical_access_score": medical_access_score,
                "park_access_score": park_access_score,
                "commercial_activity": commercial_activity,
                "ownership_complexity": ownership_complexity,
                "renewal_potential": renewal_potential,
            }
        )

    return pd.DataFrame.from_records(records)


def generate_and_store_simulation(
    seed: int = DEFAULT_SIMULATION_SEED,
    old_area_intensity: float = DEFAULT_SIMULATION_LEVEL,
    population_density: float = DEFAULT_SIMULATION_LEVEL,
    public_transport_level: float = DEFAULT_SIMULATION_LEVEL,
    green_space_level: float = DEFAULT_SIMULATION_LEVEL,
    disaster_risk_level: float = DEFAULT_SIMULATION_LEVEL,
) -> SimulationState:
    global _simulation_state
    parameters = SimulationParameters(
        random_seed=seed,
        old_area_intensity=old_area_intensity,
        population_density=population_density,
        public_transport_level=public_transport_level,
        green_space_level=green_space_level,
        disaster_risk_level=disaster_risk_level,
    ).bounded()
    frame = generate_synthetic_data(
        seed=parameters.random_seed,
        old_area_intensity=parameters.old_area_intensity,
        population_density=parameters.population_density,
        public_transport_level=parameters.public_transport_level,
        green_space_level=parameters.green_space_level,
        disaster_risk_level=parameters.disaster_risk_level,
    )
    _simulation_state = SimulationState(seed=parameters.random_seed, parameters=parameters, frame=frame)
    try:
        from app.renewal_current import clear_r01_current_data_cache

        clear_r01_current_data_cache()
    except ImportError:
        pass
    return _simulation_state


def get_simulation_state() -> SimulationState:
    if _simulation_state is None:
        return generate_and_store_simulation(DEFAULT_SIMULATION_SEED)

    return _simulation_state


def get_simulation_records() -> list[dict[str, Any]]:
    state = get_simulation_state()
    return _records_from_frame(state.frame)


def get_simulation_grid(grid_id: str) -> dict[str, Any] | None:
    state = get_simulation_state()
    matches = state.frame[state.frame["grid_id"] == grid_id]
    if matches.empty:
        return None

    return _records_from_frame(matches)[0]


def _records_from_frame(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.to_dict(orient="records")


def _bounded_int(value: float, field: str) -> int:
    return int(round(_bounded_value(value, field)))


def _bounded_score(value: float, field: str) -> float:
    return round(_bounded_value(value, field), 2)


def _bounded_ratio(value: float, field: str) -> float:
    return round(_bounded_value(value, field), 4)


def _bounded_value(value: float, field: str) -> float:
    lower, upper = FIELD_RANGES[field]
    return _clamp(value, lower, upper)


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(float(value), lower), upper)


def _level_factor(value: float) -> float:
    return (_clamp(value, 0, 100) - 50) / 50


def _emerging_residential_intensity(distance_ratio: float, x: float, y: float, center_x: float, center_y: float) -> float:
    ring_factor = 1 - abs(distance_ratio - 0.42) / 0.42
    eastern_growth = 1.0 if x > center_x else 0.72
    northern_growth = 1.0 if y > center_y - 2200 else 0.62
    return _clamp(eastern_growth * northern_growth * max(ring_factor, 0), 0, 1)
