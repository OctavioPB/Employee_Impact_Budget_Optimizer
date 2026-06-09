from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services.data_service import get_org
from backend.services.resilience_service import (
    _add_scores,
    build_resilience_data,
    run_disruption_scenario,
)

router = APIRouter()


class ScenarioRequest(BaseModel):
    scenario:      str   = "A"
    size:          str   = "small"
    scenario_type: str
    params:        dict  = {}


@router.get("/resilience")
def resilience(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented. Use demo=true.")
    try:
        return build_resilience_data(scenario.upper(), size.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resilience/scenario")
def run_scenario(body: ScenarioRequest) -> dict:
    try:
        org = get_org(body.scenario.upper(), body.size.lower())
        df  = _add_scores(org.employees.copy().reset_index(drop=True))
        return run_disruption_scenario(df, body.scenario_type, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
