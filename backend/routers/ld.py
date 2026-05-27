from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from backend.services.ld_service import (
    build_ld_data,
    run_ld_optimization,
    compute_pareto_frontier,
    _add_scores,
)
from backend.services.data_service import get_org

router = APIRouter()


class OptimizeRequest(BaseModel):
    scenario:         str   = "A"
    size:             str   = "small"
    budget:           float = 50000
    max_per_employee: int   = 2
    close_gaps:       bool  = False


class ParetoRequest(BaseModel):
    scenario:     str   = "A"
    size:         str   = "small"
    total_budget: float = 300000


@router.get("/ld")
def ld(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented. Use demo=true.")
    try:
        return build_ld_data(scenario.upper(), size.lower())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ld/optimize")
def ld_optimize(body: OptimizeRequest) -> dict:
    try:
        org = get_org(body.scenario.upper(), body.size.lower())
        df  = _add_scores(org.employees.copy().reset_index(drop=True))
        return run_ld_optimization(df, body.budget, body.max_per_employee, body.close_gaps)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ld/pareto")
def ld_pareto(body: ParetoRequest) -> list:
    try:
        org = get_org(body.scenario.upper(), body.size.lower())
        df  = _add_scores(org.employees.copy().reset_index(drop=True))
        return compute_pareto_frontier(df, body.total_budget)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
