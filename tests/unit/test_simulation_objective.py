"""Simulation objective: rank-weighted impact with a fixed cost per person kept.

Regression: maximizing the sum of raw impact (scores bunched in ~25-75) favoured
headcount, keeping only 5 of the 10 top-quintile employees at 80% of spend.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.data_service import DEFAULT_HEADCOUNT_COST, run_simulation

client = TestClient(app)


def _top_quintile_kept(result: dict) -> tuple[int, int]:
    top = [e for e in result["employees"] if e["impact_percentile"] > 80]
    return sum(e["retained"] for e in top), len(top)


@pytest.mark.parametrize("scenario", ["A", "B", "C"])
def test_top_impact_quintile_is_kept_at_default_budget(scenario):
    kept, total = _top_quintile_kept(run_simulation(scenario, "small", 80, [], [], True, True))
    assert kept == total


def test_percentiles_span_the_org():
    pcts = [e["impact_percentile"] for e in run_simulation("A", "small", 80, [], [], False, False)["employees"]]
    assert min(pcts) <= 5 and max(pcts) == 100


def test_higher_headcount_cost_never_keeps_more_people():
    counts = [run_simulation("A", "medium", 80, [], [], True, True, lam)["retained_count"] for lam in (0, 10, 30)]
    assert counts[0] >= counts[1] >= counts[2]
    assert counts[0] > counts[2]


def test_people_below_the_seat_cost_are_kept_only_when_required():
    # No constraints, generous budget, high seat cost: nobody under the 40th percentile is worth a seat
    r = run_simulation("B", "small", 95, [], [], False, False, 40)
    assert all(e["impact_percentile"] > 40 for e in r["employees"] if e["retained"])
    assert r["budget_used_pct"] < 95          # budget deliberately left unused


def test_overrides_still_win_over_the_seat_cost():
    base = run_simulation("A", "small", 80, [], [], False, False, 40)
    low = min(base["employees"], key=lambda e: e["impact_percentile"])
    r = run_simulation("A", "small", 80, [low["employee_id"]], [], False, False, 40)
    assert next(e for e in r["employees"] if e["employee_id"] == low["employee_id"])["retained"]


def test_api_exposes_objective_and_validates_headcount_cost():
    r = client.post("/api/simulate", json={})
    assert r.status_code == 200
    assert r.json()["objective"] == {"weighting": "impact_percentile", "headcount_cost": DEFAULT_HEADCOUNT_COST}
    assert client.post("/api/simulate", json={"headcount_cost": 60}).status_code == 422
    assert client.post("/api/simulate", json={"headcount_cost": -1}).status_code == 422
