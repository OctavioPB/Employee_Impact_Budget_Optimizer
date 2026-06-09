from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.data_service import generate_org_with_params, reset_cache

router = APIRouter()


class GenerateRequest(BaseModel):
    scenario:        str   = Field(default="A", pattern="^[ABCabc]$")
    size:            str   = Field(default="small", pattern="^(small|medium|large)$")
    seed:            int   = Field(default=42, ge=0, le=99999)
    org_name:        str   = Field(default="", max_length=80)
    nexus_fraction:  float = Field(default=0.15, ge=0.0, le=0.50)
    budget_variance: float = Field(default=0.10, ge=-0.30, le=0.50)


@router.post("/admin/demo/reset")
def reset_demo_cache() -> dict:
    """Clear the in-memory demo data cache. Next request regenerates fresh data."""
    count = reset_cache()
    return {"status": "ok", "cleared_entries": count}


@router.post("/admin/demo/generate")
def generate_demo(body: GenerateRequest) -> dict:
    """Generate a synthetic org with custom parameters and cache it."""
    try:
        org = generate_org_with_params(
            scenario_id=body.scenario.upper(),
            org_size=body.size.lower(),
            seed=body.seed,
            org_name_override=body.org_name.strip() or None,
            nexus_fraction_override=body.nexus_fraction,
            budget_variance_override=body.budget_variance,
        )
        return {
            "status":     "ok",
            "org_name":   org.org_name,
            "scenario_id":org.scenario_id,
            "org_size":   org.org_size,
            "headcount":  len(org.employees),
            "departments":int(org.employees["department"].nunique()),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
