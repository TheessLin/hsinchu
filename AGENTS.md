# AGENTS.md

## Project

Hsinchu Urban Resilience Health Simulation POC

## Goal

Build an interactive web GIS application that visualizes synthetic urban resilience health scores for Hsinchu City.

## Mandatory Stack

### Frontend

* React
* TypeScript
* Vite
* OpenLayers
* ECharts
* Tailwind CSS

### Backend

* Python 3.12+
* FastAPI
* Pydantic
* GeoPandas
* Pandas
* NumPy
* Shapely

### Data

* GeoJSON
* JSON
* CSV

## Core Features

1. Display the Hsinchu City study boundary.
2. Generate 500m analysis grids.
3. Generate deterministic synthetic urban data.
4. Calculate six resilience dimensions.
5. Calculate a composite resilience score from 0 to 100.
6. Render a red-yellow-green thematic map.
7. Allow users to click a grid and view its indicators.
8. Allow dimension switching.
9. Display candidate renewal-area rankings.
10. Support simulation regeneration with a fixed seed.
11. Export analysis results as GeoJSON and CSV.

## Resilience Dimensions

* Built Environment: 25%
* Disaster and Evacuation: 20%
* Transportation and Accessibility: 15%
* Social and Demographic: 15%
* Living Services and Health: 15%
* Renewal Potential: 10%

## Data Rules

Synthetic data must not be pure uncontrolled random data.

Use deterministic rules based on:

* distance to the simulated urban center
* land-use type
* building density
* development age
* public transport accessibility
* road density
* green-space accessibility

A fixed random seed may be used only to introduce limited variation after rule-based baseline values are calculated.

## Architecture Rules

* Keep frontend and backend separated.
* Put scoring logic in the backend.
* Do not calculate official policy conclusions.
* Do not use personal data.
* Do not call external APIs during runtime.
* Include a visible disclaimer that all results are simulated.
* Functions must include type hints.
* Add unit tests for scoring and candidate selection.
* Add clear setup instructions to README.md.

## Definition of Done

The project is complete when:

* frontend and backend can be started locally
* the map displays analysis grids
* colors reflect resilience scores
* clicking a grid displays detailed indicators
* dimension switching works
* candidate ranking works
* regeneration works with reproducible results
* all backend tests pass
* export functions work

# Phase 2 Rules

## Scope

Phase 2 builds a small-area urban-renewal simulation for candidate area R-01.

## Required Features

1. Generate an R-01 current-condition dataset.
2. Generate building, block, road, park, parking and POI geometries.
3. Render buildings as LOD1 extruded volumes.
4. Implement Scenario 0, A, B and C.
5. Store every scenario as parameterized JSON.
6. Recalculate KPIs whenever scenario parameters change.
7. Compare current and proposed scenarios.
8. Produce an AI-ready structured decision summary.
9. Export scenario and KPI results.
10. Keep all results deterministic and reproducible.

## Scenario Definitions

### Scenario 0

Current simulated condition.

### Scenario A

Housing-oriented renewal.

### Scenario B

Resilience-oriented renewal.

### Scenario C

Transit and commercial-oriented renewal.

## Engineering Rules

* Reuse Phase 1 APIs and components where possible.
* Do not duplicate scoring logic in the frontend.
* Put simulation formulas in backend services.
* Do not let the language model calculate official KPI values.
* AI receives only structured calculated results.
* Every scenario must preserve an audit trail of assumptions.
* Use LOD1 building geometry only.
* Avoid Cesium unless the existing implementation requires it.
* Add unit tests for every KPI formula.
* Add integration tests for scenario generation.
* Show a visible synthetic-data disclaimer.

## Phase 2 Definition of Done

Phase 2 is complete when:

* R-01 can be opened from the Phase 1 map.
* Current buildings and facilities are displayed.
* Users can switch among Scenario 0, A, B and C.
* 2D and 3D geometry updates correctly.
* KPI cards and charts update correctly.
* Before-and-after comparison works.
* AI summary uses calculated results only.
* Scenario parameters can be exported.
* All tests pass.



