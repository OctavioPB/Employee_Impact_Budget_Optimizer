"""Sprint 20 — Pulse Monitoring router."""

from fastapi import APIRouter

from backend.services.pulse_service import build_pulse_data

router = APIRouter()


@router.get("/pulse")
def pulse(scenario: str = "A", size: str = "small", demo: bool = True) -> dict:
    """Full pulse monitoring dataset: heatmap, early warning, timelines, cohesion."""
    return build_pulse_data(scenario.upper(), size.lower())
