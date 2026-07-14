from typing import Any

from app.candidates import get_candidate_area
from app.simulation import get_simulation_state

PHASE2_DATA_VERSION = "0.1.0"
SYNTHETIC_DATA_DISCLAIMER = "Synthetic simulation data only; not for official policy decisions."


def get_phase2_candidate_detail(candidate_id: str) -> dict[str, Any] | None:
    candidate = get_candidate_area(candidate_id)
    if candidate is None:
        return None

    state = get_simulation_state()
    return {
        "phase1_data_version": "0.1.0",
        "phase2_data_version": PHASE2_DATA_VERSION,
        "candidate_id": candidate["candidate_id"],
        "source_candidate_rank": candidate["candidate_rank"],
        "grid_ids": candidate["grid_ids"],
        "grid_count": candidate["grid_count"],
        "area": candidate["area"],
        "average_resilience_score": candidate["average_resilience_score"],
        "average_renewal_opportunity_score": candidate["average_renewal_opportunity_score"],
        "primary_issues": candidate["primary_issues"],
        "geometry": candidate["geometry"],
        "seed": state.seed,
        "simulation_parameters": state.parameters.as_dict(),
        "data_type": "synthetic",
        "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
    }
