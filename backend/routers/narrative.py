from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.narrative_service import (
    build_narrative_data,
    check_ollama,
    generate_attrition_explanation,
    generate_impact_explanation,
    generate_manager_brief,
    generate_simulation_summary,
)

router = APIRouter()


class GenerateRequest(BaseModel):
    scenario:    str   = "A"
    size:        str   = "small"
    employee_id: str   = ""
    budget_pct:  float = Field(default=0.80, ge=0.5, le=1.0)


@router.get("/narrative")
def narrative_data(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented.")
    try:
        return build_narrative_data(scenario.upper(), size.lower())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/narrative/status")
def ollama_status() -> dict:
    return check_ollama()


@router.post("/narrative/impact")
def impact_explanation(body: GenerateRequest) -> dict:
    if not body.employee_id:
        raise HTTPException(status_code=400, detail="employee_id required")
    try:
        return generate_impact_explanation(body.scenario.upper(), body.size.lower(), body.employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/narrative/attrition")
def attrition_explanation(body: GenerateRequest) -> dict:
    if not body.employee_id:
        raise HTTPException(status_code=400, detail="employee_id required")
    try:
        return generate_attrition_explanation(body.scenario.upper(), body.size.lower(), body.employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/narrative/simulation")
def simulation_summary(body: GenerateRequest) -> dict:
    try:
        return generate_simulation_summary(body.scenario.upper(), body.size.lower(), body.budget_pct)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/narrative/brief")
def manager_brief(body: GenerateRequest) -> dict:
    if not body.employee_id:
        raise HTTPException(status_code=400, detail="employee_id required")
    try:
        return generate_manager_brief(body.scenario.upper(), body.size.lower(), body.employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
