from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from backend.services.ohi_service import build_ohi_data, _compute_ohi, _add_scores
from backend.services.data_service import get_org

router = APIRouter()


class PreviewRequest(BaseModel):
    scenario:      str   = "A"
    size:          str   = "small"
    retention_pct: float = Field(default=0.80, ge=0.5, le=1.0)


@router.get("/ohi")
def ohi(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented.")
    try:
        return build_ohi_data(scenario.upper(), size.lower())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ohi/preview")
def ohi_preview(body: PreviewRequest) -> dict:
    """Compute OHI for a given retention scenario (what-if before execution)."""
    try:
        org = get_org(body.scenario.upper(), body.size.lower())
        df  = _add_scores(org.employees.copy().reset_index(drop=True))
        n   = len(df)
        n_ret = max(2, int(n * body.retention_pct))
        df_sub = df.nlargest(n_ret, "impact_score").reset_index(drop=True)
        result = _compute_ohi(df_sub)
        base   = _compute_ohi(df)["overall"]
        return {
            "retention_pct":     body.retention_pct,
            "n_retained":        n_ret,
            "n_total":           n,
            "ohi":               result["overall"],
            "ohi_delta":         round(result["overall"] - base, 1),
            "grade":             result["grade"],
            "sub_indices":       {k: v["score"] for k, v in result["sub_indices"].items()},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
