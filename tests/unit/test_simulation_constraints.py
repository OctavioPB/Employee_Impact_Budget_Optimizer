"""The Simulation page's leadership and critical-skills toggles must change the solve.

Regression: run_simulation used to accept both flags and ignore them.
"""

import pytest

from backend.services.data_service import (
    _greedy_retention,
    build_dashboard_data,
    run_simulation,
)


def _retained(result: dict) -> set[str]:
    return {e["employee_id"] for e in result["employees"] if e["retained"]}


@pytest.mark.parametrize("scenario", ["A", "B", "C"])
def test_enabled_constraints_give_full_coverage(scenario):
    r = run_simulation(scenario, "small", 50, [], [], True, True)
    assert r["feasible"]
    for key in ("leadership", "critical_skills"):
        cov = r["constraints"][key]
        assert cov["enabled"] is True
        assert cov["covered"] == cov["total"] > 0
        assert cov["uncovered"] == []


def test_leadership_toggle_changes_the_plan_when_budget_is_tight():
    off = run_simulation("B", "small", 50, [], [], False, False)
    on = run_simulation("B", "small", 50, [], [], True, False)
    lead_off, lead_on = off["constraints"]["leadership"], on["constraints"]["leadership"]
    assert lead_off["covered"] < lead_off["total"]        # unconstrained plan leaves a team leaderless
    assert lead_on["covered"] == lead_on["total"]         # constraint fixes it
    assert _retained(on) != _retained(off)
    assert on["total_impact"] <= off["total_impact"]      # coverage costs some impact, never adds


def test_skills_toggle_changes_the_plan_when_budget_is_tight():
    off = run_simulation("A", "small", 50, [], [], False, False)
    on = run_simulation("A", "small", 50, [], [], False, True)
    assert off["constraints"]["critical_skills"]["uncovered"]          # names the lost skills
    assert on["constraints"]["critical_skills"]["uncovered"] == []
    assert _retained(on) != _retained(off)


def test_constraints_stay_within_budget():
    r = run_simulation("A", "medium", 60, [], [], True, True)
    budget = build_dashboard_data("A", "medium")["total_budget"] * 0.60
    spent = sum(e["annual_salary"] for e in r["employees"] if e["retained"])
    assert spent <= budget + 1e-6


def test_infeasible_budget_names_the_conflicting_constraint():
    r = run_simulation("A", "small", 10, [], [], True, True)
    assert not r["feasible"]
    assert "leadership coverage" in r["infeasibility_reason"]
    assert "force-retained" not in r["infeasibility_reason"]   # none were given


def test_infeasible_overrides_are_reported_as_such():
    emps = build_dashboard_data("A", "small")["employee_table"]
    top = [e["employee_id"] for e in sorted(emps, key=lambda e: -e["annual_salary"])[:20]]
    r = run_simulation("A", "small", 30, top, [], False, False)
    assert not r["feasible"]
    assert "force-retained" in r["infeasibility_reason"]


def test_greedy_fallback_covers_every_group_first():
    cands = [
        {"employee_id": "A", "impact_score": 90, "annual_salary": 100},
        {"employee_id": "B", "impact_score": 10, "annual_salary": 50},   # only holder of group 2
        {"employee_id": "C", "impact_score": 80, "annual_salary": 60},
    ]
    weights = {"A": 100.0, "B": 10.0, "C": 70.0}
    ok, kept = _greedy_retention(cands, 160, set(), [["B"], ["A", "C"]], weights, 0.0)
    assert ok
    assert "B" in kept and kept & {"A", "C"}
    ok, _ = _greedy_retention(cands, 40, set(), [["B"]], weights, 0.0)   # cheapest holder exceeds budget
    assert not ok


def test_greedy_fallback_skips_people_below_the_headcount_cost():
    cands = [
        {"employee_id": "A", "impact_score": 90, "annual_salary": 100},
        {"employee_id": "B", "impact_score": 10, "annual_salary": 10},
    ]
    ok, kept = _greedy_retention(cands, 1_000, set(), [], {"A": 100.0, "B": 20.0}, 30.0)
    assert ok and kept == {"A"}          # budget remains, but B ranks below the seat cost
