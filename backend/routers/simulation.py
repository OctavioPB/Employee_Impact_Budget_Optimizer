from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.data_service import run_simulation

router = APIRouter()


class SimulationRequest(BaseModel):
    scenario:              str       = Field(default="A", pattern="^[ABCabc]$")
    size:                  str       = Field(default="small", pattern="^(small|medium|large)$")
    budget_pct:            float     = Field(default=80.0, ge=10.0, le=200.0)
    force_retain:          list[str] = Field(default_factory=list)
    exclude:               list[str] = Field(default_factory=list)
    leadership_constraint: bool      = Field(default=True)
    skills_constraint:     bool      = Field(default=True)


@router.post("/simulate")
def simulate(body: SimulationRequest) -> dict:
    try:
        return run_simulation(
            scenario=body.scenario.upper(),
            size=body.size.lower(),
            budget_pct=body.budget_pct,
            force_retain=body.force_retain,
            exclude=body.exclude,
            leadership_constraint=body.leadership_constraint,
            skills_constraint=body.skills_constraint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
