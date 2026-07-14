# Hsinchu Urban Resilience Health Simulation POC

新竹市都市韌性與 R-01 都市更新 Scenario 模擬概念驗證系統。系統使用合成資料呈現第一階段城市網格韌性分析，以及第二階段 R-01 小範圍都市更新方案比較。

> 本系統使用 POC 模擬資料，不得作為正式政策判斷、真實都市更新結論或法定審議依據。

## Stack

Frontend:

* React
* TypeScript
* Vite
* OpenLayers
* ECharts
* Tailwind CSS
* Three.js for Phase 2 LOD1 extrusion

Backend:

* Python 3.12+
* FastAPI
* Pydantic
* GeoPandas
* Pandas
* NumPy
* Shapely

## Architecture

```text
frontend/
  src/App.tsx                    Phase 1 dashboard and R-01 navigation
  src/RenewalCandidatePage.tsx   Phase 2 Scenario UI, 2D/3D map, KPI, AI summary, export
  src/api.ts                     Runtime API calls and GitHub Pages static-demo routing

backend/app/
  main.py                        FastAPI routes
  grids.py                       Hsinchu boundary and 500m grid generation
  simulation.py                  deterministic Phase 1 synthetic data engine
  resilience.py                  Phase 1 resilience scoring
  candidates.py                  renewal candidate clustering and ranking
  phase2.py                      Phase 1 to Phase 2 R-01 handoff
  renewal_current.py             R-01 current-condition synthetic generator
  renewal_scenarios.py           Scenario 0/A/B/C parameterized engine
  renewal_kpis.py                Scenario KPI service and comparison
  renewal_summary.py             rule-based AI Decision Summary provider
  renewal_exports.py             Phase 2 ranking and export service
```

All scoring, KPI, ranking, Scenario, export, and summary evidence values are produced by the backend. The frontend displays results and sends Scenario parameters only after the user clicks `重新模擬`.

## Install

From the repository root:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Frontend:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\frontend
pnpm install
```

## Start Locally

Terminal 1:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\frontend
pnpm dev
```

Open:

```text
http://127.0.0.1:5173/
```

## Main APIs

Health:

```text
GET /api/v1/health
```

Phase 1:

```text
GET  /api/boundary
GET  /api/grids
POST /api/simulation/generate
GET  /api/resilience
GET  /api/candidates
GET  /api/export/grids.geojson
GET  /api/export/indicators.csv
GET  /api/export/candidates.geojson
```

Phase 2 R-01:

```text
GET  /api/v1/phase2/candidates/R-01
GET  /api/renewal/R-01/current
GET  /api/renewal/R-01/scenarios
GET  /api/renewal/R-01/scenarios/{scenario_id}
POST /api/renewal/R-01/scenarios/{scenario_id}/run
POST /api/renewal/R-01/scenarios/{scenario_id}/run-kpis
GET  /api/renewal/R-01/scenarios/{scenario_id}/kpis
GET  /api/renewal/R-01/comparison
GET  /api/renewal/R-01/scenarios/{scenario_id}/summary
GET  /api/renewal/R-01/recommendation
```

Phase 2 export:

```text
GET /api/renewal/R-01/export/scenarios/{scenario_id}.json
GET /api/renewal/R-01/export/scenarios/{scenario_id}/buildings.geojson
GET /api/renewal/R-01/export/scenarios/{scenario_id}/roads.geojson
GET /api/renewal/R-01/export/scenarios/{scenario_id}/facilities.geojson
GET /api/renewal/R-01/export/scenarios/{scenario_id}/kpis.csv
GET /api/renewal/R-01/export/scenarios/{scenario_id}/decision-summary.json
```

`scenario_id` supports `0`, `A`, `B`, and `C`.

## GitHub Pages Static Demo

GitHub Pages cannot run FastAPI, so the project exports a static snapshot into `frontend/public/demo-data`.

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc
python scripts\export_static_demo.py

cd frontend
$env:VITE_STATIC_DEMO="1"
$env:VITE_BASE_PATH="/"
pnpm build
pnpm preview
```

Static demo limitations:

* The Pages version is a fixed snapshot generated from the selected seed.
* `重新模擬` returns static pre-exported Scenario results instead of running a backend.
* No external API is called at runtime.

## Tests

Backend:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc
pytest
```

Frontend build check:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\frontend
pnpm build
```

## Known Limits

* All urban, building, road, facility, KPI, and AI summary values are synthetic POC values.
* R-01 is a simulated candidate handoff from Phase 1; it must not be described as a real problem area.
* 3D uses LOD1 extrusion only. No LOD2, facade texture, BIM, CFD, or real address data is included.
* Objective ranking is based on backend-calculated KPI values and POC objective definitions, not an official policy evaluation.
