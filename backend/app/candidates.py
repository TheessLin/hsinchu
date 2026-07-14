from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping
from shapely.ops import unary_union

from app.grids import BASE_CRS, GRID_CRS, generate_analysis_grids
from app.resilience import DIMENSION_WEIGHTS, get_resilience_records

RESILIENCE_THRESHOLD = 45
RENEWAL_OPPORTUNITY_THRESHOLD = 60
MIN_CLUSTER_SIZE = 2

DIMENSION_ISSUE_LABELS: dict[str, str] = {
    "built_environment_score": "\u5efa\u6210\u74b0\u5883",
    "disaster_evacuation_score": "\u707d\u5bb3\u8207\u907f\u96e3",
    "transport_access_score": "\u4ea4\u901a\u53ef\u53ca",
    "social_demographic_score": "\u793e\u6703\u4eba\u53e3",
    "living_health_score": "\u751f\u6d3b\u670d\u52d9\u8207\u5065\u5eb7",
    "renewal_potential_score": "\u66f4\u65b0\u6a5f\u6703\u8207\u6574\u5408\u689d\u4ef6",
}


def get_candidate_areas() -> list[dict[str, Any]]:
    grids = generate_analysis_grids()
    records = get_resilience_records()
    return build_candidate_areas(records, grids)


def get_candidate_area(candidate_id: str) -> dict[str, Any] | None:
    for candidate in get_candidate_areas():
        if candidate["candidate_id"] == candidate_id:
            return candidate

    return None


def build_candidate_areas(records: list[dict[str, Any]], grids: gpd.GeoDataFrame) -> list[dict[str, Any]]:
    score_frame = pd.DataFrame.from_records(records)
    if score_frame.empty:
        return []

    required_fields = {"grid_id", "resilience_score", "renewal_potential", *DIMENSION_WEIGHTS.keys()}
    missing_fields = required_fields - set(score_frame.columns)
    if missing_fields:
        raise ValueError(f"Candidate input records are missing fields: {sorted(missing_fields)}")

    projected_grids = grids.to_crs(GRID_CRS)[["grid_id", "geometry"]].copy()
    candidate_scores = score_frame[
        (score_frame["resilience_score"] < RESILIENCE_THRESHOLD)
        & (score_frame["renewal_potential"] >= RENEWAL_OPPORTUNITY_THRESHOLD)
    ].copy()
    if candidate_scores.empty:
        return []

    candidate_grids = projected_grids.merge(candidate_scores, on="grid_id", how="inner")
    candidate_grids = gpd.GeoDataFrame(candidate_grids, geometry="geometry", crs=GRID_CRS)
    components = _connected_components(candidate_grids)
    ranked_candidates = [_candidate_from_component(component, index) for index, component in enumerate(components)]
    ranked_candidates.sort(
        key=lambda candidate: (
            -candidate["_screening_score"],
            candidate["average_resilience_score"],
            -candidate["average_renewal_opportunity_score"],
            -candidate["grid_count"],
        )
    )

    for rank, candidate in enumerate(ranked_candidates, start=1):
        candidate["candidate_rank"] = rank
        candidate["candidate_id"] = f"R-{rank:02d}"
        del candidate["_screening_score"]

    return ranked_candidates


def _connected_components(candidate_grids: gpd.GeoDataFrame) -> list[gpd.GeoDataFrame]:
    geometries = list(candidate_grids.geometry)
    neighbors: dict[int, set[int]] = {index: set() for index in range(len(candidate_grids))}

    for left_index, left_geometry in enumerate(geometries):
        for right_index in range(left_index + 1, len(geometries)):
            intersection = left_geometry.intersection(geometries[right_index])
            if not intersection.is_empty and intersection.length > 0:
                neighbors[left_index].add(right_index)
                neighbors[right_index].add(left_index)

    visited: set[int] = set()
    components: list[gpd.GeoDataFrame] = []
    for start_index in range(len(candidate_grids)):
        if start_index in visited:
            continue

        stack = [start_index]
        component_indices: list[int] = []
        visited.add(start_index)
        while stack:
            current = stack.pop()
            component_indices.append(current)
            for neighbor in neighbors[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)

        if len(component_indices) >= MIN_CLUSTER_SIZE:
            components.append(candidate_grids.iloc[component_indices].copy())

    return components


def _candidate_from_component(component: gpd.GeoDataFrame, index: int) -> dict[str, Any]:
    geometry = unary_union(list(component.geometry))
    geojson_geometry = gpd.GeoSeries([geometry], crs=GRID_CRS).to_crs(BASE_CRS).iloc[0]
    average_resilience = round(float(component["resilience_score"].mean()), 2)
    average_renewal_opportunity = round(float(component["renewal_potential"].mean()), 2)
    screening_score = round((100 - average_resilience) * 0.65 + average_renewal_opportunity * 0.35, 2)

    return {
        "candidate_id": f"R-{index + 1:02d}",
        "grid_count": int(len(component)),
        "grid_ids": sorted(str(grid_id) for grid_id in component["grid_id"].tolist()),
        "area": round(float(geometry.area), 2),
        "average_resilience_score": average_resilience,
        "average_renewal_opportunity_score": average_renewal_opportunity,
        "primary_issues": _primary_issues(component),
        "candidate_rank": index + 1,
        "geometry": mapping(geojson_geometry),
        "_screening_score": screening_score,
    }


def _primary_issues(component: gpd.GeoDataFrame) -> list[str]:
    dimension_averages = [
        (field, float(component[field].mean()))
        for field in DIMENSION_WEIGHTS
    ]
    dimension_averages.sort(key=lambda item: item[1])
    return [DIMENSION_ISSUE_LABELS[field] for field, _score in dimension_averages[:3]]
