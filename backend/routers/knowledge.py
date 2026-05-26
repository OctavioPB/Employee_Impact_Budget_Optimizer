from fastapi import APIRouter, Query, HTTPException

from backend.services.knowledge_service import build_knowledge_data

router = APIRouter()


@router.get("/knowledge")
def knowledge(
    scenario: str  = Query(default="A", pattern="^[ABCabc]$"),
    size:     str  = Query(default="small", pattern="^(small|medium|large)$"),
    demo:     bool = Query(default=True),
) -> dict:
    if not demo:
        raise HTTPException(status_code=501, detail="Live data mode not yet implemented. Use demo=true.")
    try:
        return build_knowledge_data(scenario.upper(), size.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
