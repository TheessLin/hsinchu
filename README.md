# Hsinchu Urban Resilience Health Simulation POC

Interactive web GIS proof of concept for visualizing simulated urban resilience health scores in Hsinchu City.

This repository currently contains the project scaffold, user-provided Hsinchu City district boundaries, backend-generated 500m analysis grids, a rule-based synthetic data engine, and an OpenLayers grid viewer. Resilience scoring, rankings, and export logic are intentionally not implemented yet.

## Stack

Frontend:

* React
* TypeScript
* Vite
* OpenLayers
* ECharts
* Tailwind CSS

Backend:

* Python 3.12+
* FastAPI
* Pydantic
* GeoPandas
* Pandas
* NumPy
* Shapely

## Project Structure

```text
hsinchu-urban-resilience-poc/
|-- backend/
|   |-- app/
|   |   |-- __init__.py
|   |   |-- grids.py
|   |   |-- simulation.py
|   |   `-- main.py
|   `-- requirements.txt
|-- data/
|   `-- base/
|       |-- hsinchu_city_administrative_boundary.geojson
|       |-- hsinchu_city_district_boundaries.geojson
|       `-- hsinchu_city_study_boundary.geojson
|-- frontend/
|   |-- src/
|   |   |-- App.tsx
|   |   |-- main.tsx
|   |   `-- styles.css
|   |-- package.json
|   `-- vite.config.ts
|-- docs/
|-- scripts/
`-- tests/
```

## Backend Setup

From the repository root:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Start the API:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
GET http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "hsinchu-resilience-api",
  "version": "0.1.0"
}
```

Grid and boundary APIs:

```text
GET http://127.0.0.1:8000/api/boundary
GET http://127.0.0.1:8000/api/grids
```

Both endpoints return GeoJSON `FeatureCollection` responses. The boundary API returns the three Hsinchu City districts: `北區`, `東區`, and `香山區`. The grid API returns 500m x 500m analysis cells that intersect the city boundary union. Each grid feature includes `grid_id`, `centroid_x`, `centroid_y`, `district_type`, and `land_use_type`.

Simulation APIs:

```text
POST http://127.0.0.1:8000/api/simulation/generate
GET  http://127.0.0.1:8000/api/simulation/data
GET  http://127.0.0.1:8000/api/simulation/grid/{grid_id}
```

Generate request body:

```json
{
  "seed": 42
}
```

The simulation engine is deterministic for a fixed seed. It generates rule-based synthetic values from distance to the simulated urban core, district type, land-use type, density, accessibility, open-space, and limited seeded variation.

Resilience scoring APIs:

```text
GET http://127.0.0.1:8000/api/resilience
GET http://127.0.0.1:8000/api/resilience/{grid_id}
```

The scoring engine returns six dimension scores, a weighted `resilience_score`, and `score_details` for each dimension. High scores mean better resilience health. The original `renewal_potential` value is preserved as a renewal pressure indicator, while `renewal_potential_score` is the inverse resilience-health score used in the weighted total.

## Frontend Setup

In a second terminal:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\frontend
pnpm install
pnpm dev
```

Open:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Tests

Run backend tests from the repository root:

```powershell
pytest
```

Run frontend build checks:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\frontend
pnpm build
```

## Current Scope

Implemented:

* FastAPI app factory
* `/api/v1/health`
* CORS for the local Vite frontend
* User-provided local Hsinchu City district boundaries normalized to EPSG:4326
* Backend-generated 500m analysis grids
* `/api/boundary` and `/api/grids` GeoJSON APIs
* Rule-based deterministic synthetic data engine
* `/api/simulation/generate`, `/api/simulation/data`, and `/api/simulation/grid/{grid_id}` APIs
* Urban resilience scoring engine with six dimension scores and calculation details
* `/api/resilience` and `/api/resilience/{grid_id}` APIs
* React + TypeScript + Vite frontend scaffold
* Tailwind CSS setup
* Interactive dashboard with OpenLayers thematic grid rendering
* Red-yellow-green resilience score map by selected dimension
* Grid hover tooltip and click selection
* Right-side grid diagnosis panel with radar chart, top issues, and indicator details
* Bottom candidate ranking and dimension comparison chart
* Visible simulated-data disclaimer
* Basic backend tests

Not implemented yet:

* Analysis result GeoJSON and CSV export
