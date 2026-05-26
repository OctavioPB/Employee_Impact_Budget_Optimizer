"""Collaborative Decision Room — Sprint 14.

Implements:
  - Session lifecycle: Draft → Active → Under Review → Finalized
  - Participant roles: Owner, Participant, Observer
  - Override management with conflict detection (retain vs exclude same employee)
  - Conflict resolution modes: last_write, owner, vote
  - Structured deliberation: comment threads, proposals, objections, votes
  - Digital sign-off and immutable finalization
  - Full activity feed per session

State is held in an in-memory dict and persisted to a JSON sidecar file,
simulating PostgreSQL persistence (fully recoverable after all participants
disconnect and reconnect).
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── Persistence ───────────────────────────────────────────────────────────────
_DATA_DIR  = Path(__file__).resolve().parents[2] / "backend" / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_STORE_FILE = _DATA_DIR / "decision_rooms.json"

_SESSIONS: dict[str, dict] = {}

_DEMO_PARTICIPANTS = [
    {"user_id": "u_chen",    "display_name": "Director Chen",        "role": "Owner"},
    {"user_id": "u_rivera",  "display_name": "HR Partner Rivera",    "role": "Participant"},
    {"user_id": "u_hoffman", "display_name": "Manager Hoffman",      "role": "Participant"},
    {"user_id": "u_okonkwo", "display_name": "Finance Lead Okonkwo", "role": "Observer"},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _uid() -> str:
    return str(uuid.uuid4())[:8]


def _load() -> None:
    global _SESSIONS
    if _STORE_FILE.exists():
        try:
            _SESSIONS = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _SESSIONS = {}


def _save() -> None:
    _STORE_FILE.write_text(
        json.dumps(_SESSIONS, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _log(session: dict, actor: str, action: str, subject: str) -> None:
    session["activity"].append({
        "id":        _uid(),
        "timestamp": _now(),
        "actor":     actor,
        "action":    action,
        "subject":   subject,
    })


def _detect_conflicts(session: dict) -> None:
    """Rebuild conflict list from current overrides."""
    overrides = session["overrides"]
    retain_map  = {o["employee_id"]: o for o in overrides if o["override_type"] == "retain"}
    exclude_map = {o["employee_id"]: o for o in overrides if o["override_type"] == "exclude"}

    existing_conflicts = {c["employee_id"]: c for c in session["conflicts"]}
    new_conflicts: list[dict] = []

    for eid, r_ov in retain_map.items():
        if eid in exclude_map:
            e_ov = exclude_map[eid]
            existing = existing_conflicts.get(eid)
            if existing and existing.get("resolved"):
                new_conflicts.append(existing)
            else:
                new_conflicts.append({
                    "employee_id":   eid,
                    "employee_name": r_ov["employee_name"],
                    "retain_by":     r_ov["set_by"],
                    "exclude_by":    e_ov["set_by"],
                    "resolved":      False,
                    "resolution":    None,
                    "resolved_by":   None,
                    "resolved_at":   None,
                })

    session["conflicts"] = new_conflicts


def _load_once() -> None:
    if not _SESSIONS:
        _load()


# ── Public API ────────────────────────────────────────────────────────────────

def list_sessions() -> list[dict]:
    _load_once()
    return list(_SESSIONS.values())


def create_session(
    name: str,
    owner_name: str,
    owner_id: str,
    scenario: str,
    size: str,
    budget_pct: float,
    resolution_mode: str = "owner",
) -> dict:
    _load_once()
    sid = _uid()
    session: dict = {
        "session_id":       sid,
        "name":             name,
        "scenario":         scenario,
        "size":             size,
        "budget_pct":       budget_pct,
        "resolution_mode":  resolution_mode,
        "status":           "Draft",
        "created_at":       _now(),
        "participants": [{
            "user_id":      owner_id,
            "display_name": owner_name,
            "role":         "Owner",
            "last_action":  "Created session",
            "joined_at":    _now(),
        }],
        "overrides":   [],
        "conflicts":   [],
        "comments":    [],
        "proposals":   [],
        "sign_offs":   [],
        "activity":    [],
    }
    _log(session, owner_name, "created", f'Session "{name}"')
    _SESSIONS[sid] = session
    _save()
    return session


def get_session(session_id: str) -> dict:
    _load_once()
    if session_id not in _SESSIONS:
        raise KeyError(f"Session {session_id} not found")
    return _SESSIONS[session_id]


def join_session(session_id: str, user_id: str, display_name: str, role: str) -> dict:
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session is finalized — no new participants")

    for p in session["participants"]:
        if p["user_id"] == user_id:
            p["last_action"] = "Rejoined"
            _save()
            return session

    session["participants"].append({
        "user_id":      user_id,
        "display_name": display_name,
        "role":         role,
        "last_action":  "Joined",
        "joined_at":    _now(),
    })
    _log(session, display_name, "joined", f"as {role}")
    _save()
    return session


def update_status(session_id: str, new_status: str, updated_by: str) -> dict:
    session = get_session(session_id)
    valid = {"Draft", "Active", "Under Review", "Finalized"}
    if new_status not in valid:
        raise ValueError(f"Invalid status: {new_status}")
    if session["status"] == "Finalized":
        raise ValueError("Finalized sessions are immutable")
    old = session["status"]
    session["status"] = new_status
    _log(session, updated_by, "changed status", f"{old} → {new_status}")
    _save()
    return session


def add_override(
    session_id: str,
    employee_id: str,
    employee_name: str,
    override_type: str,
    set_by: str,
    rationale: str,
) -> dict:
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session is finalized")
    if override_type not in ("retain", "exclude"):
        raise ValueError(f"Invalid override_type: {override_type}")

    # Remove any existing override for this employee from this user
    session["overrides"] = [
        o for o in session["overrides"]
        if not (o["employee_id"] == employee_id and o["set_by"] == set_by)
    ]
    session["overrides"].append({
        "id":            _uid(),
        "employee_id":   employee_id,
        "employee_name": employee_name,
        "override_type": override_type,
        "set_by":        set_by,
        "rationale":     rationale,
        "timestamp":     _now(),
    })
    _detect_conflicts(session)
    _log(session, set_by, f"{override_type}_override", employee_name)

    _update_participant_action(session, set_by, f"Set {override_type} for {employee_name}")
    _save()
    return session


def remove_override(session_id: str, employee_id: str, set_by: str) -> dict:
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session is finalized")

    before = len(session["overrides"])
    session["overrides"] = [
        o for o in session["overrides"]
        if not (o["employee_id"] == employee_id and o["set_by"] == set_by)
    ]
    if len(session["overrides"]) < before:
        _detect_conflicts(session)
        _log(session, set_by, "removed_override", employee_id)
        _update_participant_action(session, set_by, f"Removed override for {employee_id}")
    _save()
    return session


def resolve_conflict(
    session_id: str,
    employee_id: str,
    resolution: str,
    resolved_by: str,
) -> dict:
    """resolution must be 'retain' or 'exclude'."""
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session is finalized")

    for conflict in session["conflicts"]:
        if conflict["employee_id"] == employee_id and not conflict["resolved"]:
            conflict["resolved"]    = True
            conflict["resolution"]  = resolution
            conflict["resolved_by"] = resolved_by
            conflict["resolved_at"] = _now()

            # Apply winning override — remove the losing one
            losing_type = "exclude" if resolution == "retain" else "retain"
            session["overrides"] = [
                o for o in session["overrides"]
                if not (o["employee_id"] == employee_id and o["override_type"] == losing_type)
            ]
            _log(session, resolved_by, "resolved_conflict",
                 f"{conflict['employee_name']} → {resolution}")
            _update_participant_action(session, resolved_by,
                                        f"Resolved conflict for {conflict['employee_name']}")
            break
    _save()
    return session


def add_comment(
    session_id: str,
    employee_id: str,
    employee_name: str,
    author: str,
    body: str,
) -> dict:
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session is finalized")
    session["comments"].append({
        "id":            _uid(),
        "employee_id":   employee_id,
        "employee_name": employee_name,
        "author":        author,
        "body":          body,
        "timestamp":     _now(),
    })
    _log(session, author, "commented_on", employee_name)
    _update_participant_action(session, author, f"Commented on {employee_name}")
    _save()
    return session


def add_proposal(
    session_id: str,
    employee_id: str,
    employee_name: str,
    override_type: str,
    rationale: str,
    proposed_by: str,
) -> dict:
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session is finalized")
    proposal = {
        "id":            _uid(),
        "employee_id":   employee_id,
        "employee_name": employee_name,
        "override_type": override_type,
        "rationale":     rationale,
        "proposed_by":   proposed_by,
        "timestamp":     _now(),
        "objections":    [],
        "votes":         {},
        "vote_open":     False,
        "vote_result":   None,
        "applied":       False,
    }
    session["proposals"].append(proposal)
    _log(session, proposed_by, "proposed", f"{override_type} {employee_name}: {rationale[:60]}")
    _update_participant_action(session, proposed_by, f"Proposed {override_type} for {employee_name}")
    _save()
    return session


def add_objection(
    session_id: str,
    proposal_id: str,
    objector: str,
    reason: str,
) -> dict:
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session is finalized")
    for proposal in session["proposals"]:
        if proposal["id"] == proposal_id:
            proposal["objections"].append({
                "objector":  objector,
                "reason":    reason,
                "timestamp": _now(),
            })
            _log(session, objector, "objected_to",
                 f"proposal: {proposal['override_type']} {proposal['employee_name']}")
            _update_participant_action(session, objector, f"Objected to proposal on {proposal['employee_name']}")
            break
    _save()
    return session


def open_vote(session_id: str, proposal_id: str, opened_by: str) -> dict:
    session = get_session(session_id)
    for proposal in session["proposals"]:
        if proposal["id"] == proposal_id:
            proposal["vote_open"] = True
            _log(session, opened_by, "opened_vote",
                 f"on {proposal['override_type']} {proposal['employee_name']}")
            break
    _save()
    return session


def cast_vote(
    session_id: str,
    proposal_id: str,
    voter: str,
    decision: str,
) -> dict:
    session = get_session(session_id)
    if decision not in ("yes", "no"):
        raise ValueError(f"Invalid vote: {decision}")
    for proposal in session["proposals"]:
        if proposal["id"] == proposal_id:
            if not proposal["vote_open"]:
                raise ValueError("Vote is not open")
            proposal["votes"][voter] = decision
            _log(session, voter, "voted", f"{decision} on {proposal['employee_name']}")
            _update_participant_action(session, voter, f"Voted {decision} on {proposal['employee_name']}")

            # Auto-close: check if all non-observer participants voted
            voters_needed = [
                p["display_name"] for p in session["participants"]
                if p["role"] != "Observer"
            ]
            if all(v in proposal["votes"] for v in voters_needed):
                yes_count = sum(1 for v in proposal["votes"].values() if v == "yes")
                no_count  = sum(1 for v in proposal["votes"].values() if v == "no")
                result     = "passed" if yes_count > no_count else "failed"
                proposal["vote_open"]   = False
                proposal["vote_result"] = result
                _log(session, "System", "vote_closed",
                     f"{proposal['employee_name']} → {result} ({yes_count}Y/{no_count}N)")
                if result == "passed":
                    _apply_proposal(session, proposal)
            break
    _save()
    return session


def _apply_proposal(session: dict, proposal: dict) -> None:
    if proposal["applied"]:
        return
    add_override(
        session["session_id"],
        proposal["employee_id"],
        proposal["employee_name"],
        proposal["override_type"],
        proposal["proposed_by"],
        f"[Vote passed] {proposal['rationale']}",
    )
    proposal["applied"] = True


def sign_off(
    session_id: str,
    user_id: str,
    display_name: str,
    comment: str,
) -> dict:
    session = get_session(session_id)
    if session["status"] == "Finalized":
        raise ValueError("Session already finalized")

    # Idempotent: replace existing sign-off from same user
    session["sign_offs"] = [s for s in session["sign_offs"] if s["user_id"] != user_id]
    session["sign_offs"].append({
        "user_id":      user_id,
        "display_name": display_name,
        "comment":      comment,
        "timestamp":    _now(),
    })
    _log(session, display_name, "signed_off", "")

    # Auto-finalize when all non-observer participants sign
    required = [p for p in session["participants"] if p["role"] in ("Owner", "Participant")]
    signed_ids = {s["user_id"] for s in session["sign_offs"]}
    if all(p["user_id"] in signed_ids for p in required):
        session["status"] = "Finalized"
        _log(session, "System", "finalized", "All required approvers signed off")

    _update_participant_action(session, display_name, "Signed off")
    _save()
    return session


def _update_participant_action(session: dict, display_name: str, action: str) -> None:
    for p in session["participants"]:
        if p["display_name"] == display_name:
            p["last_action"] = action
            break


def seed_demo_session(scenario: str, size: str) -> dict:
    """Create a pre-populated demo session if no sessions exist yet."""
    _load_once()
    if _SESSIONS:
        return next(iter(_SESSIONS.values()))

    session = create_session(
        name            = "Q3 Budget Review — Engineering",
        owner_name      = "Director Chen",
        owner_id        = "u_chen",
        scenario        = scenario,
        size            = size,
        budget_pct      = 85.0,
        resolution_mode = "owner",
    )
    sid = session["session_id"]

    for p in _DEMO_PARTICIPANTS[1:]:
        join_session(sid, p["user_id"], p["display_name"], p["role"])

    update_status(sid, "Active", "Director Chen")
    return _SESSIONS[sid]
