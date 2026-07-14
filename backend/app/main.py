from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.candidates import get_candidate_area, get_candidate_areas
from app.exports import get_candidate_geojson, get_grid_analysis_geojson, get_indicator_csv
from app.grids import get_boundary_geojson, get_grid_geojson
from app.phase2 import get_phase2_candidate_detail
from app.resilience import get_resilience_grid, get_resilience_records
from app.renewal_current import (
    get_r01_blocks_geojson,
    get_r01_buildings_geojson,
    get_r01_current_payload,
    get_r01_facilities_geojson,
    get_r01_roads_geojson,
)
from app.renewal_exports import (
    get_r01_comparison_with_rankings,
    get_r01_decision_summary_export,
    get_r01_scenario_export,
    get_r01_scenario_kpi_csv,
    get_r01_scenario_layer_geojson,
)
from app.renewal_kpis import build_r01_scenario_kpis, get_r01_scenario_kpis
from app.renewal_scenarios import ScenarioRunRequest, list_r01_scenarios, get_r01_scenario, normalize_scenario_id, run_r01_scenario
from app.renewal_summary import build_r01_decision_summary, get_r01_recommendation, get_r01_scenario_summary
from app.simulation import generate_and_store_simulation, get_simulation_grid, get_simulation_records, get_simulation_state

API_PREFIX = "/api/v1"
SERVICE_NAME = "hsinchu-resilience-api"
VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SimulationGenerateRequest(BaseModel):
    random_seed: int | None = None
    seed: int | None = None
    old_area_intensity: float = 50
    population_density: float = 50
    public_transport_level: float = 50
    green_space_level: float = 50
    disaster_risk_level: float = 50

    def resolved_seed(self) -> int:
        if self.random_seed is not None:
            return self.random_seed
        if self.seed is not None:
            return self.seed
        return 42


class SimulationGenerateResponse(BaseModel):
    status: str
    seed: int
    parameters: dict[str, float | int]
    grid_count: int


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hsinchu Urban Resilience Health Simulation API",
        version=VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{API_PREFIX}/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service=SERVICE_NAME, version=VERSION)

    @app.get("/api/boundary")
    @app.get(f"{API_PREFIX}/boundary")
    def boundary() -> dict[str, object]:
        return get_boundary_geojson()

    @app.get("/api/grids")
    @app.get(f"{API_PREFIX}/grids")
    def grids() -> dict[str, object]:
        return get_grid_geojson()

    @app.post("/api/simulation/generate", response_model=SimulationGenerateResponse)
    @app.post(f"{API_PREFIX}/simulation/generate", response_model=SimulationGenerateResponse)
    def generate_simulation(request: SimulationGenerateRequest | None = None) -> SimulationGenerateResponse:
        payload = request or SimulationGenerateRequest()
        state = generate_and_store_simulation(
            seed=payload.resolved_seed(),
            old_area_intensity=payload.old_area_intensity,
            population_density=payload.population_density,
            public_transport_level=payload.public_transport_level,
            green_space_level=payload.green_space_level,
            disaster_risk_level=payload.disaster_risk_level,
        )
        return SimulationGenerateResponse(
            status="generated",
            seed=state.seed,
            parameters=state.parameters.as_dict(),
            grid_count=len(state.frame),
        )

    @app.get("/api/simulation/data")
    @app.get(f"{API_PREFIX}/simulation/data")
    def simulation_data() -> dict[str, Any]:
        state = get_simulation_state()
        return {
            "seed": state.seed,
            "parameters": state.parameters.as_dict(),
            "count": len(state.frame),
            "records": get_simulation_records(),
        }

    @app.get("/api/simulation/grid/{grid_id}")
    @app.get(f"{API_PREFIX}/simulation/grid/{{grid_id}}")
    def simulation_grid(grid_id: str) -> dict[str, Any]:
        record = get_simulation_grid(grid_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Grid not found: {grid_id}")

        return record

    @app.get("/api/resilience")
    @app.get(f"{API_PREFIX}/resilience")
    def resilience() -> dict[str, Any]:
        records = get_resilience_records()
        return {
            "count": len(records),
            "records": records,
        }

    @app.get("/api/resilience/{grid_id}")
    @app.get(f"{API_PREFIX}/resilience/{{grid_id}}")
    def resilience_grid(grid_id: str) -> dict[str, Any]:
        record = get_resilience_grid(grid_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Grid not found: {grid_id}")

        return record

    @app.get("/api/candidates")
    @app.get(f"{API_PREFIX}/candidates")
    def candidates() -> dict[str, Any]:
        candidate_areas = get_candidate_areas()
        return {
            "count": len(candidate_areas),
            "records": candidate_areas,
        }

    @app.get("/api/candidates/{candidate_id}")
    @app.get(f"{API_PREFIX}/candidates/{{candidate_id}}")
    def candidate(candidate_id: str) -> dict[str, Any]:
        candidate_area = get_candidate_area(candidate_id)
        if candidate_area is None:
            raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")

        return candidate_area

    @app.get("/api/phase2/candidates/{candidate_id}")
    @app.get(f"{API_PREFIX}/phase2/candidates/{{candidate_id}}")
    def phase2_candidate(candidate_id: str) -> dict[str, Any]:
        detail = get_phase2_candidate_detail(candidate_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Phase 2 candidate not found: {candidate_id}")

        return detail

    @app.get("/api/renewal/R-01/current")
    @app.get(f"{API_PREFIX}/renewal/R-01/current")
    def r01_current() -> dict[str, Any]:
        return get_r01_current_payload()

    @app.get("/api/renewal/R-01/blocks")
    @app.get(f"{API_PREFIX}/renewal/R-01/blocks")
    def r01_blocks() -> dict[str, Any]:
        return get_r01_blocks_geojson()

    @app.get("/api/renewal/R-01/buildings")
    @app.get(f"{API_PREFIX}/renewal/R-01/buildings")
    def r01_buildings() -> dict[str, Any]:
        return get_r01_buildings_geojson()

    @app.get("/api/renewal/R-01/roads")
    @app.get(f"{API_PREFIX}/renewal/R-01/roads")
    def r01_roads() -> dict[str, Any]:
        return get_r01_roads_geojson()

    @app.get("/api/renewal/R-01/facilities")
    @app.get(f"{API_PREFIX}/renewal/R-01/facilities")
    def r01_facilities() -> dict[str, Any]:
        return get_r01_facilities_geojson()

    @app.get("/api/renewal/R-01/scenarios")
    @app.get(f"{API_PREFIX}/renewal/R-01/scenarios")
    def r01_scenarios() -> dict[str, Any]:
        return list_r01_scenarios()

    @app.get("/api/renewal/R-01/scenarios/{scenario_id}")
    @app.get(f"{API_PREFIX}/renewal/R-01/scenarios/{{scenario_id}}")
    def r01_scenario(scenario_id: str) -> dict[str, Any]:
        scenario = get_r01_scenario(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        return scenario

    @app.post("/api/renewal/R-01/scenarios/{scenario_id}/run")
    @app.post(f"{API_PREFIX}/renewal/R-01/scenarios/{{scenario_id}}/run")
    def run_r01_scenario_api(scenario_id: str, request: ScenarioRunRequest | None = None) -> dict[str, Any]:
        normalized = normalize_scenario_id(scenario_id)
        if normalized is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        return run_r01_scenario(normalized, request or ScenarioRunRequest())

    @app.post("/api/renewal/R-01/scenarios/{scenario_id}/run-kpis")
    @app.post(f"{API_PREFIX}/renewal/R-01/scenarios/{{scenario_id}}/run-kpis")
    def run_r01_scenario_kpis_api(scenario_id: str, request: ScenarioRunRequest | None = None) -> dict[str, Any]:
        normalized = normalize_scenario_id(scenario_id)
        if normalized is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        scenario = run_r01_scenario(normalized, request or ScenarioRunRequest())
        kpis = build_r01_scenario_kpis(scenario)
        if kpis is None:
            raise HTTPException(status_code=500, detail=f"Scenario KPIs could not be calculated: {scenario_id}")
        summary = build_r01_decision_summary(scenario, kpis)
        if summary is None:
            raise HTTPException(status_code=500, detail=f"Scenario summary could not be calculated: {scenario_id}")
        return {"scenario": scenario, "kpis": kpis, "summary": summary}

    @app.get("/api/renewal/R-01/scenarios/{scenario_id}/kpis")
    @app.get(f"{API_PREFIX}/renewal/R-01/scenarios/{{scenario_id}}/kpis")
    def r01_scenario_kpis(scenario_id: str) -> dict[str, Any]:
        payload = get_r01_scenario_kpis(scenario_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        return payload

    @app.get("/api/renewal/R-01/comparison")
    @app.get(f"{API_PREFIX}/renewal/R-01/comparison")
    def r01_scenario_comparison() -> dict[str, Any]:
        return get_r01_comparison_with_rankings()

    @app.get("/api/renewal/R-01/scenarios/{scenario_id}/summary")
    @app.get(f"{API_PREFIX}/renewal/R-01/scenarios/{{scenario_id}}/summary")
    def r01_scenario_summary(scenario_id: str) -> dict[str, Any]:
        summary = get_r01_scenario_summary(scenario_id)
        if summary is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        return summary

    @app.get("/api/renewal/R-01/recommendation")
    @app.get(f"{API_PREFIX}/renewal/R-01/recommendation")
    def r01_recommendation() -> dict[str, Any]:
        return get_r01_recommendation()

    @app.get("/api/renewal/R-01/export/scenarios/{scenario_id}.json")
    @app.get(f"{API_PREFIX}/renewal/R-01/export/scenarios/{{scenario_id}}.json")
    def export_r01_scenario_json(scenario_id: str) -> dict[str, Any]:
        payload = get_r01_scenario_export(scenario_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        return payload

    @app.get("/api/renewal/R-01/export/scenarios/{scenario_id}/{layer}.geojson")
    @app.get(f"{API_PREFIX}/renewal/R-01/export/scenarios/{{scenario_id}}/{{layer}}.geojson")
    def export_r01_scenario_layer_geojson(scenario_id: str, layer: str) -> dict[str, Any]:
        payload = get_r01_scenario_layer_geojson(scenario_id, layer)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Scenario layer not found: {scenario_id}/{layer}")
        return payload

    @app.get("/api/renewal/R-01/export/scenarios/{scenario_id}/kpis.csv")
    @app.get(f"{API_PREFIX}/renewal/R-01/export/scenarios/{{scenario_id}}/kpis.csv")
    def export_r01_scenario_kpi_csv(scenario_id: str) -> Response:
        payload = get_r01_scenario_kpi_csv(scenario_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        return Response(
            content=payload,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="r01_scenario_{scenario_id.upper()}_kpis.csv"'},
        )

    @app.get("/api/renewal/R-01/export/scenarios/{scenario_id}/decision-summary.json")
    @app.get(f"{API_PREFIX}/renewal/R-01/export/scenarios/{{scenario_id}}/decision-summary.json")
    def export_r01_decision_summary_json(scenario_id: str) -> dict[str, Any]:
        payload = get_r01_decision_summary_export(scenario_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
        return payload

    @app.get("/api/export/grids.geojson")
    @app.get(f"{API_PREFIX}/export/grids.geojson")
    def export_grids_geojson() -> dict[str, Any]:
        return get_grid_analysis_geojson()

    @app.get("/api/export/indicators.csv")
    @app.get(f"{API_PREFIX}/export/indicators.csv")
    def export_indicators_csv() -> Response:
        return Response(
            content=get_indicator_csv(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="hsinchu_indicators.csv"'},
        )

    @app.get("/api/export/candidates.geojson")
    @app.get(f"{API_PREFIX}/export/candidates.geojson")
    def export_candidates_geojson() -> dict[str, Any]:
        return get_candidate_geojson()

    return app


app = create_app()
