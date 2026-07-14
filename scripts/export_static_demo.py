from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.candidates import get_candidate_areas  # noqa: E402
from app.grids import get_boundary_geojson, get_grid_geojson  # noqa: E402
from app.phase2 import get_phase2_candidate_detail  # noqa: E402
from app.renewal_exports import (  # noqa: E402
    get_r01_comparison_with_rankings,
    get_r01_decision_summary_export,
    get_r01_scenario_export,
    get_r01_scenario_kpi_csv,
    get_r01_scenario_layer_geojson,
)
from app.renewal_current import (  # noqa: E402
    get_r01_blocks_geojson,
    get_r01_buildings_geojson,
    get_r01_current_payload,
    get_r01_facilities_geojson,
    get_r01_roads_geojson,
)
from app.renewal_kpis import get_r01_scenario_kpis  # noqa: E402
from app.renewal_scenarios import get_r01_scenario, list_r01_scenarios  # noqa: E402
from app.renewal_summary import get_r01_recommendation, get_r01_scenario_summary  # noqa: E402
from app.resilience import get_resilience_records  # noqa: E402
from app.simulation import generate_and_store_simulation  # noqa: E402

OUTPUT_DIR = ROOT / "frontend" / "public" / "demo-data"


def main() -> None:
    seed = int(os.environ.get("STATIC_DEMO_SEED", "42"))
    state = generate_and_store_simulation(seed=seed)
    resilience_records = get_resilience_records()
    candidate_areas = get_candidate_areas()
    phase2_candidate = get_phase2_candidate_detail("R-01")
    if phase2_candidate is None:
        raise RuntimeError("R-01 candidate is not available for static demo export.")

    write_json("health.json", {"status": "ok", "service": "hsinchu-resilience-api-static-demo", "version": "0.1.0"})
    write_json("boundary.json", get_boundary_geojson())
    write_json("grids.json", get_grid_geojson())
    write_json(
        "simulation-generate.json",
        {
            "status": "generated",
            "seed": state.seed,
            "parameters": state.parameters.as_dict(),
            "grid_count": len(state.frame),
            "static_demo": True,
        },
    )
    write_json("resilience.json", {"count": len(resilience_records), "records": resilience_records})
    write_json("candidates.json", {"count": len(candidate_areas), "records": candidate_areas})
    write_json("phase2-candidate-R-01.json", phase2_candidate)
    write_json("renewal-current.json", get_r01_current_payload())
    write_json("renewal-blocks.json", get_r01_blocks_geojson())
    write_json("renewal-buildings.json", get_r01_buildings_geojson())
    write_json("renewal-roads.json", get_r01_roads_geojson())
    write_json("renewal-facilities.json", get_r01_facilities_geojson())
    write_json("renewal-scenarios.json", list_r01_scenarios())
    for scenario_id in ["0", "A", "B", "C"]:
        scenario = get_r01_scenario(scenario_id)
        if scenario is None:
            raise RuntimeError(f"Scenario is not available for static demo export: {scenario_id}")
        write_json(f"renewal-scenario-{scenario_id}.json", scenario)
        kpis = get_r01_scenario_kpis(scenario_id)
        if kpis is None:
            raise RuntimeError(f"Scenario KPIs are not available for static demo export: {scenario_id}")
        summary = get_r01_scenario_summary(scenario_id)
        if summary is None:
            raise RuntimeError(f"Scenario summary is not available for static demo export: {scenario_id}")
        write_json(f"renewal-scenario-{scenario_id}-kpis.json", kpis)
        write_json(f"renewal-scenario-{scenario_id}-run-kpis.json", {"scenario": scenario, "kpis": kpis, "summary": summary})
        write_json(f"renewal-scenario-{scenario_id}-summary.json", summary)
        write_json(f"renewal-scenario-{scenario_id}-export.json", get_r01_scenario_export(scenario_id))
        write_json(f"renewal-scenario-{scenario_id}-decision-summary.json", get_r01_decision_summary_export(scenario_id))
        kpi_csv = get_r01_scenario_kpi_csv(scenario_id)
        if kpi_csv is None:
            raise RuntimeError(f"Scenario KPI CSV is not available for static demo export: {scenario_id}")
        write_text(f"renewal-scenario-{scenario_id}-kpis.csv", kpi_csv)
        for layer in ["buildings", "roads", "facilities"]:
            layer_payload = get_r01_scenario_layer_geojson(scenario_id, layer)
            if layer_payload is None:
                raise RuntimeError(f"Scenario layer is not available for static demo export: {scenario_id}/{layer}")
            write_json(f"renewal-scenario-{scenario_id}-{layer}.geojson", layer_payload)
    write_json("renewal-comparison.json", get_r01_comparison_with_rankings())
    write_json("renewal-recommendation.json", get_r01_recommendation())

    print(f"Exported static demo data to {OUTPUT_DIR}")


def write_json(filename: str, payload: Any) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, default=json_default), encoding="utf-8")


def write_text(filename: str, payload: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(payload, encoding="utf-8")


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


if __name__ == "__main__":
    main()
