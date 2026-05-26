from fastapi import APIRouter, Query, HTTPException

from backend.services.compensation_service import build_compensation_data

router = APIRouter()


@router.get("/compensation")
def compensation(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented. Use demo=true.")
    try:
        return build_compensation_data(scenario.upper(), size.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
