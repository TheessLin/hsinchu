# Data Schema

## Simulation Record

Each synthetic simulation record is keyed by `grid_id` and represents one 500m x 500m analysis grid.

Base fields:

| Field | Type | Notes |
| --- | --- | --- |
| `grid_id` | string | Stable grid identifier, for example `HC-GRID-0001`. |
| `centroid_x` | number | Grid centroid longitude, EPSG:4326. |
| `centroid_y` | number | Grid centroid latitude, EPSG:4326. |
| `district_type` | string | One of `北區`, `東區`, `香山區`. |
| `land_use_type` | string | Rule-based land-use class assigned by the backend. |

Synthetic fields:

| Field | Type | Range |
| --- | --- | --- |
| `population` | integer | 30-2400 |
| `daytime_population` | integer | 20-3200 |
| `elderly_ratio` | number | 0.06-0.32 |
| `child_ratio` | number | 0.05-0.22 |
| `building_count` | integer | 1-120 |
| `average_building_age` | integer | 3-60 |
| `old_building_ratio` | number | 0.02-0.85 |
| `building_coverage_ratio` | number | 0.08-0.82 |
| `narrow_road_ratio` | number | 0.05-0.75 |
| `open_space_ratio` | number | 0.03-0.65 |
| `green_ratio` | number | 0.02-0.55 |
| `parking_supply` | integer | 0-900 |
| `parking_demand` | integer | 0-1400 |
| `bus_access_score` | number | 0-100 |
| `bike_access_score` | number | 0-100 |
| `walkability_score` | number | 0-100 |
| `shelter_access_score` | number | 0-100 |
| `fire_risk` | number | 0-100 |
| `flood_risk` | number | 0-100 |
| `medical_access_score` | number | 0-100 |
| `park_access_score` | number | 0-100 |
| `commercial_activity` | number | 0-100 |
| `ownership_complexity` | number | 0-100 |
| `renewal_potential` | number | 0-100 |

## Generation Rules

The backend synthetic data engine is deterministic for a fixed seed. It first computes rule-based baselines from distance to the simulated urban core, district type, land-use type, density, accessibility, open-space, and risk proxies. Seeded variation is applied only after baseline values are calculated, then every field is clamped to its schema range.

## Resilience Score Record

The resilience scoring engine extends each simulation record with six dimension scores, one composite score, and calculation details.

Score fields:

| Field | Type | Range | Weight |
| --- | --- | --- | --- |
| `built_environment_score` | number | 0-100 | 0.25 |
| `disaster_evacuation_score` | number | 0-100 | 0.20 |
| `transport_access_score` | number | 0-100 | 0.15 |
| `social_demographic_score` | number | 0-100 | 0.15 |
| `living_health_score` | number | 0-100 | 0.15 |
| `renewal_potential_score` | number | 0-100 | 0.10 |
| `resilience_score` | number | 0-100 | weighted total |

Composite formula:

```text
resilience_score =
  built_environment_score * 0.25 +
  disaster_evacuation_score * 0.20 +
  transport_access_score * 0.15 +
  social_demographic_score * 0.15 +
  living_health_score * 0.15 +
  renewal_potential_score * 0.10
```

High scores represent better resilience health. Risk or pressure indicators are inverted before scoring.

`renewal_potential` remains the original synthetic renewal-pressure field, where a higher value means higher renewal potential or pressure. `renewal_potential_score` is the inverse resilience-health score used in the composite score, so higher `renewal_potential_score` means lower renewal pressure and better current health.

Each score record includes:

| Field | Type | Notes |
| --- | --- | --- |
| `score_details` | object | Calculation details keyed by dimension score field. |
| `score_details.<dimension>.score` | number | Dimension score from 0 to 100. |
| `score_details.<dimension>.components` | object | Component scores used in the dimension. |
| `score_details.<dimension>.weights` | object | Weights applied to the component scores. |
| `score_details.renewal_potential_score.raw_renewal_potential` | number | Original non-inverted renewal potential value. |
