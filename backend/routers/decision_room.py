from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import decision_room_service as svc

router = APIRouter()


# ── Request bodies ────────────────────────────────────────────────────────────

class CreateSessionBody(BaseModel):
    name:            str
    owner_name:      str
    owner_id:        str
    scenario:        str   = "A"
    size:            str   = "small"
    budget_pct:      float = 85.0
    resolution_mode: str   = "owner"


class JoinBody(BaseModel):
    user_id:      str
    display_name: str
    role:         str = "Participant"


class StatusBody(BaseModel):
    new_status:  str
    updated_by:  str


class OverrideBody(BaseModel):
    employee_id:   str
    employee_name: str
    override_type: str
    set_by:        str
    rationale:     str = ""


class RemoveOverrideBody(BaseModel):
    set_by: str


class ResolveBody(BaseModel):
    resolution:  str
    resolved_by: str


class CommentBody(BaseModel):
    employee_id:   str
    employee_name: str
    author:        str
    body:          str


class ProposalBody(BaseModel):
    employee_id:   str
    employee_name: str
    override_type: str
    rationale:     str
    proposed_by:   str


class ObjectionBody(BaseModel):
    objector: str
    reason:   str


class VoteBody(BaseModel):
    voter:    str
    decision: str


class OpenVoteBody(BaseModel):
    opened_by: str


class SignOffBody(BaseModel):
    user_id:      str
    display_name: str
    comment:      str = ""


class SeedBody(BaseModel):
    scenario: str = "A"
    size:     str = "small"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/decision-room/sessions")
def list_sessions() -> list[dict]:
    return svc.list_sessions()


@router.post("/decision-room/sessions")
def create_session(body: CreateSessionBody) -> dict:
    return _wrap(svc.create_session,
                 body.name, body.owner_name, body.owner_id,
                 body.scenario, body.size, body.budget_pct, body.resolution_mode)


@router.post("/decision-room/sessions/seed")
def seed(body: SeedBody) -> dict:
    return _wrap(svc.seed_demo_session, body.scenario, body.size)


@router.get("/decision-room/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    return _wrap(svc.get_session, session_id)


@router.post("/decision-room/sessions/{session_id}/join")
def join(session_id: str, body: JoinBody) -> dict:
    return _wrap(svc.join_session, session_id, body.user_id, body.display_name, body.role)


@router.put("/decision-room/sessions/{session_id}/status")
def update_status(session_id: str, body: StatusBody) -> dict:
    return _wrap(svc.update_status, session_id, body.new_status, body.updated_by)


@router.post("/decision-room/sessions/{session_id}/overrides")
def add_override(session_id: str, body: OverrideBody) -> dict:
    return _wrap(svc.add_override, session_id,
                 body.employee_id, body.employee_name,
                 body.override_type, body.set_by, body.rationale)


@router.delete("/decision-room/sessions/{session_id}/overrides/{employee_id}")
def remove_override(session_id: str, employee_id: str, body: RemoveOverrideBody) -> dict:
    return _wrap(svc.remove_override, session_id, employee_id, body.set_by)


@router.post("/decision-room/sessions/{session_id}/conflicts/{employee_id}/resolve")
def resolve_conflict(session_id: str, employee_id: str, body: ResolveBody) -> dict:
    return _wrap(svc.resolve_conflict, session_id, employee_id, body.resolution, body.resolved_by)


@router.post("/decision-room/sessions/{session_id}/comments")
def add_comment(session_id: str, body: CommentBody) -> dict:
    return _wrap(svc.add_comment, session_id,
                 body.employee_id, body.employee_name, body.author, body.body)


@router.post("/decision-room/sessions/{session_id}/proposals")
def add_proposal(session_id: str, body: ProposalBody) -> dict:
    return _wrap(svc.add_proposal, session_id,
                 body.employee_id, body.employee_name,
                 body.override_type, body.rationale, body.proposed_by)


@router.post("/decision-room/sessions/{session_id}/proposals/{proposal_id}/objection")
def add_objection(session_id: str, proposal_id: str, body: ObjectionBody) -> dict:
    return _wrap(svc.add_objection, session_id, proposal_id, body.objector, body.reason)


@router.post("/decision-room/sessions/{session_id}/proposals/{proposal_id}/open-vote")
def open_vote(session_id: str, proposal_id: str, body: OpenVoteBody) -> dict:
    return _wrap(svc.open_vote, session_id, proposal_id, body.opened_by)


@router.post("/decision-room/sessions/{session_id}/proposals/{proposal_id}/vote")
def cast_vote(session_id: str, proposal_id: str, body: VoteBody) -> dict:
    return _wrap(svc.cast_vote, session_id, proposal_id, body.voter, body.decision)


@router.post("/decision-room/sessions/{session_id}/sign-off")
def sign_off(session_id: str, body: SignOffBody) -> dict:
    return _wrap(svc.sign_off, session_id, body.user_id, body.display_name, body.comment)
