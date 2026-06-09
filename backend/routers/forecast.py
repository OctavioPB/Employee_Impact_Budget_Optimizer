from fastapi import APIRouter, HTTPException, Query

from backend.services.data_service import build_forecast_data, build_montecarlo_data

router = APIRouter()


@router.get("/forecast/budget")
def budget_forecast(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented. Use demo=true.")
    try:
        return build_forecast_data(scenario.upper(), size.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/forecast/montecarlo")
def monte_carlo(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented. Use demo=true.")
    try:
        return build_montecarlo_data(scenario.upper(), size.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
