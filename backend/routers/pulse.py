"""Sprint 20 — Pulse Monitoring router."""

from fastapi import APIRouter, Query

from backend.services.pulse_service import build_pulse_data

router = APIRouter()


@router.get("/pulse")
def pulse(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    """Full pulse monitoring dataset: heatmap, early warning, timelines, cohesion."""
    return build_pulse_data(scenario.upper(), size.lower())
