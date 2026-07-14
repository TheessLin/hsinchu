from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from app.grids import BASE_CRS
from app.phase2 import SYNTHETIC_DATA_DISCLAIMER
from app.renewal_current import R01_CANDIDATE_ID, to_feature_collection
from app.renewal_kpis import apply_scenario, get_r01_scenario_comparison, get_r01_scenario_kpis
from app.renewal_scenarios import get_r01_scenario, normalize_scenario_id
from app.renewal_summary import get_r01_scenario_summary

ObjectiveId = str

OBJECTIVE_DEFINITIONS: dict[ObjectiveId, dict[str, Any]] = {
    "resilience": {
        "label": "綜合韌性",
        "kpi_ids": ["resilience_score"],
        "sort_field": "value",
    },
    "housing": {
        "label": "住宅供給",
        "kpi_ids": ["residential_units"],
        "sort_field": "value",
    },
    "parking": {
        "label": "停車改善",
        "kpi_ids": ["parking_gap"],
        "sort_field": "value",
    },
    "green_open_space": {
        "label": "綠地及開放空間",
        "kpi_ids": ["green_ratio", "open_space_ratio", "park_area_m2"],
        "sort_field": "objective_score",
    },
    "transport": {
        "label": "交通可達",
        "kpi_ids": ["bus_access_score", "bike_access_score", "walkability_score"],
        "sort_field": "objective_score",
    },
    "disaster": {
        "label": "防災避難",
        "kpi_ids": ["emergency_access_score", "shelter_service_population"],
        "sort_field": "objective_score",
    },
}


def get_r01_comparison_with_rankings() -> dict[str, Any]:
    comparison = get_r01_scenario_comparison()
    comparison["objective_definitions"] = OBJECTIVE_DEFINITIONS
    comparison["rankings"] = build_objective_rankings(comparison)
    return comparison


def build_objective_rankings(comparison: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    scenarios = comparison.get("scenarios", [])
    rankings: dict[str, list[dict[str, Any]]] = {}
    for objective_id, definition in OBJECTIVE_DEFINITIONS.items():
        rows = [_ranking_row(scenario, objective_id, definition) for scenario in scenarios]
        rows.sort(key=lambda row: (row["rank_score"] is not None, row["rank_score"] or float("-inf")), reverse=True)
        rankings[objective_id] = [
            {
                **row,
                "rank": index + 1,
            }
            for index, row in enumerate(rows)
        ]
    return rankings


def get_r01_scenario_export(scenario_id: str) -> dict[str, Any] | None:
    scenario = get_r01_scenario(scenario_id)
    if scenario is None:
        return None
    kpis = get_r01_scenario_kpis(scenario_id)
    summary = get_r01_scenario_summary(scenario_id)
    return {
        "candidate_id": R01_CANDIDATE_ID,
        "scenario": scenario,
        "kpis": kpis,
        "decision_summary": summary,
        "data_type": "synthetic",
        "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
    }


def get_r01_scenario_layer_geojson(scenario_id: str, layer: str) -> dict[str, Any] | None:
    scenario = get_r01_scenario(scenario_id)
    if scenario is None:
        return None
    applied = apply_scenario_to_default_current(scenario)
    frame_by_layer = {
        "buildings": applied.buildings,
        "roads": applied.roads,
        "facilities": applied.facilities,
    }
    frame = frame_by_layer.get(layer)
    if frame is None:
        return None
    collection = to_feature_collection(frame, int(scenario["simulation_seed"]), layer)
    collection["metadata"].update(
        {
            "scenario_id": scenario["scenario_id"],
            "scenario_name": scenario["scenario_name"],
            "crs_output": BASE_CRS,
            "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
        }
    )
    return collection


def get_r01_scenario_kpi_csv(scenario_id: str) -> str | None:
    payload = get_r01_scenario_kpis(scenario_id)
    if payload is None:
        return None
    output = StringIO()
    fieldnames = [
        "scenario_id",
        "scenario_name",
        "kpi_id",
        "name",
        "value",
        "unit",
        "baseline_value",
        "absolute_change",
        "percentage_change",
        "formula_reference",
        "confidence_level",
        "reason",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for record in payload["records"]:
        writer.writerow(
            {
                "scenario_id": payload["scenario_id"],
                "scenario_name": payload["scenario_name"],
                "kpi_id": record["kpi_id"],
                "name": record["name"],
                "value": record["value"],
                "unit": record["unit"],
                "baseline_value": record["baseline_value"],
                "absolute_change": record["absolute_change"],
                "percentage_change": record["percentage_change"],
                "formula_reference": record["formula_reference"],
                "confidence_level": record["confidence_level"],
                "reason": record["reason"],
            }
        )
    return output.getvalue()


def get_r01_decision_summary_export(scenario_id: str) -> dict[str, Any] | None:
    summary = get_r01_scenario_summary(scenario_id)
    if summary is None:
        return None
    return {
        "candidate_id": R01_CANDIDATE_ID,
        "summary": summary,
        "data_type": "synthetic",
        "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
    }


def apply_scenario_to_default_current(scenario: dict[str, Any]) -> Any:
    from app.renewal_current import get_r01_current_data

    return apply_scenario(get_r01_current_data(), scenario)


def _ranking_row(scenario: dict[str, Any], objective_id: str, definition: dict[str, Any]) -> dict[str, Any]:
    kpis = scenario.get("kpis", {})
    kpi_ids = list(definition["kpi_ids"])
    evidence = [kpis[kpi_id] for kpi_id in kpi_ids if kpi_id in kpis]
    score = _objective_score(evidence)
    if definition["sort_field"] == "value" and evidence:
        score = evidence[0].get("value")
    return {
        "objective_id": objective_id,
        "objective_label": definition["label"],
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["scenario_name"],
        "rank_score": score,
        "kpi_ids": kpi_ids,
        "evidence": [
            {
                "kpi_id": record["kpi_id"],
                "name": record["name"],
                "value": record["value"],
                "unit": record["unit"],
                "baseline_value": record["baseline_value"],
                "absolute_change": record["absolute_change"],
            }
            for record in evidence
        ],
    }


def _objective_score(records: list[dict[str, Any]]) -> float | None:
    values = [_normalized_objective_value(record) for record in records]
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 4)


def _normalized_objective_value(record: dict[str, Any]) -> float | None:
    value = record.get("value")
    if not isinstance(value, (int, float)):
        return None
    unit = str(record.get("unit", ""))
    if unit == "比例":
        return float(value) * 100
    if record.get("kpi_id") == "park_area_m2":
        return min(float(value) / 80, 100)
    if record.get("kpi_id") == "shelter_service_population":
        return min(float(value) / 120, 100)
    return float(value)
