from io import StringIO
from typing import Any

import geopandas as gpd
import pandas as pd

from app.candidates import get_candidate_areas
from app.grids import BASE_CRS, generate_analysis_grids
from app.resilience import get_resilience_records
from app.simulation import get_simulation_state


def get_grid_analysis_geojson() -> dict[str, Any]:
    grids = generate_analysis_grids()
    records = pd.DataFrame.from_records(get_resilience_records())
    if records.empty:
        return {"type": "FeatureCollection", "features": []}

    joined = grids.merge(records, on=["grid_id", "centroid_x", "centroid_y", "district_type", "land_use_type"], how="left")
    joined = gpd.GeoDataFrame(joined, geometry="geometry", crs=grids.crs).to_crs(BASE_CRS)
    if "score_details" in joined.columns:
        joined["score_details"] = joined["score_details"].apply(lambda value: value if isinstance(value, dict) else {})
    return joined.__geo_interface__


def get_indicator_csv() -> str:
    state = get_simulation_state()
    output = StringIO()
    state.frame.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue()


def get_candidate_geojson() -> dict[str, Any]:
    candidates = get_candidate_areas()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    key: value
                    for key, value in candidate.items()
                    if key != "geometry"
                },
                "geometry": candidate["geometry"],
            }
            for candidate in candidates
        ],
    }
