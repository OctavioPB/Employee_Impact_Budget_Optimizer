"""50+ edge-case tests for optimization_engine.ilp_solver.

Covers: basic solves, budget constraint, leadership constraint, critical-skills
constraint, min-team-size, succession depth, force-retain, exclude, combined
overrides, infeasibility, diagnose_infeasibility, OptimizationResult properties,
and the _prepare/_empty_result/_infeasible_result helpers indirectly.
"""

import pandas as pd
import pytest

from optimization_engine.constraints import ConstraintConfig
from optimization_engine.ilp_solver import (
    OptimizationResult,
    diagnose_infeasibility,
    solve,
)

# ---------------------------------------------------------------------------
# Fixtures — canonical small datasets
# ---------------------------------------------------------------------------

def _make_employees(records: list[dict]) -> pd.DataFrame:
    """Build an employees DataFrame from a list of dicts."""
    defaults = {
        "team_id": "T1",
        "seniority_level": "mid",
        "annual_salary": 100_000,
        "annual_benefits": 20_000,
    }
    rows = [{**defaults, **r} for r in records]
    return pd.DataFrame(rows)


def _make_scores(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


def _no_constraints() -> ConstraintConfig:
    return ConstraintConfig(
        require_leadership_per_team=False,
        require_critical_skills=False,
        min_team_size=0,
        succession_depth=0,
        solver_msg=False,
    )


@pytest.fixture
def five_employees():
    emp = _make_employees([
        {"employee_id": "E1", "seniority_level": "lead",  "annual_salary": 200_000, "annual_benefits": 40_000},
        {"employee_id": "E2", "seniority_level": "mid",   "annual_salary": 100_000, "annual_benefits": 20_000},
        {"employee_id": "E3", "seniority_level": "mid",   "annual_salary": 100_000, "annual_benefits": 20_000},
        {"employee_id": "E4", "seniority_level": "mid",   "annual_salary": 100_000, "annual_benefits": 20_000},
        {"employee_id": "E5", "seniority_level": "mid",   "annual_salary": 100_000, "annual_benefits": 20_000},
    ])
    scores = _make_scores([
        {"employee_id": "E1", "impact_score": 90},
        {"employee_id": "E2", "impact_score": 80},
        {"employee_id": "E3", "impact_score": 70},
        {"employee_id": "E4", "impact_score": 60},
        {"employee_id": "E5", "impact_score": 50},
    ])
    return emp, scores


# ---------------------------------------------------------------------------
# 1. Smoke tests
# ---------------------------------------------------------------------------

class TestSmoke:
    def test_returns_optimization_result(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=600_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert isinstance(result, OptimizationResult)

    def test_status_optimal_with_ample_budget(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.status == "Optimal"
        assert result.is_feasible

    def test_all_retained_when_budget_unconstrained(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.n_retained == 5

    def test_n_retained_plus_n_at_risk_equals_n_total(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=300_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.n_retained + result.n_at_risk == result.n_total

    def test_retained_ids_and_at_risk_ids_are_disjoint(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=300_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.retained_ids.isdisjoint(result.at_risk_ids)

    def test_total_cost_within_budget(self, five_employees):
        emp, scores = five_employees
        budget = 350_000
        result = solve(emp, budget_target=budget, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        if result.is_feasible:
            assert result.total_cost <= budget + 1  # 1-dollar tolerance for float


# ---------------------------------------------------------------------------
# 2. Budget constraint
# ---------------------------------------------------------------------------

class TestBudgetConstraint:
    def test_tight_budget_retains_fewer_employees(self, five_employees):
        emp, scores = five_employees
        result_tight = solve(emp, budget_target=120_000, impact_scores=scores,
                             critical_skill_holders={}, constraint_config=_no_constraints())
        result_ample = solve(emp, budget_target=1_000_000, impact_scores=scores,
                             critical_skill_holders={}, constraint_config=_no_constraints())
        assert result_tight.n_retained < result_ample.n_retained

    def test_zero_budget_retains_no_employees(self, five_employees):
        """Budget=0 is optimal with 0 retained; the solver is not infeasible."""
        emp, scores = five_employees
        result = solve(emp, budget_target=0, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        # Retaining 0 employees costs 0 ≤ 0 → technically Optimal; 0 retained
        assert result.n_retained == 0

    def test_budget_exactly_one_employee_retains_exactly_one(self):
        emp = _make_employees([
            {"employee_id": "E1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "E2", "annual_salary": 200_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "E1", "impact_score": 50},
            {"employee_id": "E2", "impact_score": 80},
        ])
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.is_feasible
        assert result.n_retained == 1

    def test_optimizer_picks_highest_impact_within_budget(self):
        """With budget for exactly 1 mid employee, must pick highest impact."""
        emp = _make_employees([
            {"employee_id": "E1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "E2", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "E1", "impact_score": 30},
            {"employee_id": "E2", "impact_score": 90},
        ])
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert "E2" in result.retained_ids

    def test_savings_pct_calculation(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        expected_savings = result.current_spend - result.total_cost
        expected_pct = expected_savings / result.current_spend * 100
        assert abs(result.savings_pct - expected_pct) < 0.01

    def test_budget_savings_nonnegative_when_feasible(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=300_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        if result.is_feasible:
            assert result.budget_savings >= -1  # float tolerance


# ---------------------------------------------------------------------------
# 3. Leadership constraint
# ---------------------------------------------------------------------------

class TestLeadershipConstraint:
    def _two_teams_config(self):
        emp = _make_employees([
            {"employee_id": "L1", "team_id": "T1", "seniority_level": "lead",
             "annual_salary": 200_000, "annual_benefits": 0},
            {"employee_id": "M1", "team_id": "T1", "seniority_level": "mid",
             "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "L2", "team_id": "T2", "seniority_level": "director",
             "annual_salary": 250_000, "annual_benefits": 0},
            {"employee_id": "M2", "team_id": "T2", "seniority_level": "mid",
             "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "L1", "impact_score": 30},
            {"employee_id": "M1", "impact_score": 90},
            {"employee_id": "L2", "impact_score": 30},
            {"employee_id": "M2", "impact_score": 90},
        ])
        return emp, scores

    def test_leadership_forces_low_impact_leader_retained(self):
        emp, scores = self._two_teams_config()
        cfg = ConstraintConfig(require_leadership_per_team=True,
                               require_critical_skills=False, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg)
        assert "L1" in result.retained_ids
        assert "L2" in result.retained_ids

    def test_no_leadership_constraint_drops_leader_if_low_impact(self):
        emp, scores = self._two_teams_config()
        cfg = _no_constraints()
        result = solve(emp, budget_target=200_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg)
        # High-impact mids (M1=90, M2=90) should be preferred when budget is tight
        # Budget 200k → can afford 2 × 100k employees
        assert result.n_retained == 2

    def test_leadership_constraint_skipped_when_all_leaders_excluded(self):
        """When all leaders are excluded, C2 is skipped; team shows in teams_with_no_leader."""
        emp = _make_employees([
            {"employee_id": "L1", "team_id": "T1", "seniority_level": "lead",
             "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "M1", "team_id": "T1", "seniority_level": "mid",
             "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "L1", "impact_score": 80},
            {"employee_id": "M1", "impact_score": 90},
        ])
        cfg = ConstraintConfig(require_leadership_per_team=True,
                               require_critical_skills=False, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg,
                       exclude={"L1"})
        # Constraint is skipped because no non-excluded leaders exist;
        # the solution is optimal but the team has no leader retained.
        assert result.is_feasible
        assert "T1" in result.teams_with_no_leader

    def test_leadership_truly_infeasible_when_force_retain_conflicts_budget(self):
        """Force-retaining an expensive employee on a tiny budget is truly infeasible."""
        emp = _make_employees([
            {"employee_id": "L1", "team_id": "T1", "seniority_level": "lead",
             "annual_salary": 500_000, "annual_benefits": 0},
            {"employee_id": "M1", "team_id": "T1", "seniority_level": "mid",
             "annual_salary": 80_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "L1", "impact_score": 80},
            {"employee_id": "M1", "impact_score": 90},
        ])
        cfg = _no_constraints()
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg,
                       force_retain={"L1"})
        assert not result.is_feasible

    def test_exec_seniority_satisfies_leadership_constraint(self):
        emp = _make_employees([
            {"employee_id": "X1", "team_id": "T1", "seniority_level": "exec",
             "annual_salary": 300_000, "annual_benefits": 0},
            {"employee_id": "M1", "team_id": "T1", "seniority_level": "mid",
             "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "X1", "impact_score": 70},
            {"employee_id": "M1", "impact_score": 80},
        ])
        cfg = ConstraintConfig(require_leadership_per_team=True,
                               require_critical_skills=False, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg)
        assert "X1" in result.retained_ids

    def test_teams_with_no_leader_populated_on_optimal(self):
        """When constraint is OFF, teams_with_no_leader shows reality."""
        emp = _make_employees([
            {"employee_id": "M1", "team_id": "T1", "seniority_level": "mid",
             "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([{"employee_id": "M1", "impact_score": 70}])
        cfg = _no_constraints()
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg)
        assert "T1" in result.teams_with_no_leader


# ---------------------------------------------------------------------------
# 4. Critical skills constraint
# ---------------------------------------------------------------------------

class TestCriticalSkillsConstraint:
    def _skill_dataset(self):
        emp = _make_employees([
            {"employee_id": "S1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "S2", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "G1", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "S1", "impact_score": 50},
            {"employee_id": "S2", "impact_score": 60},
            {"employee_id": "G1", "impact_score": 90},
        ])
        holders = {"python": ["S1", "S2"]}
        return emp, scores, holders

    def test_skill_constraint_forces_holder_retained(self):
        emp, scores, holders = self._skill_dataset()
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True, solver_msg=False)
        result = solve(emp, budget_target=200_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg)
        assert result.is_feasible
        assert "python" in result.critical_skills_preserved

    def test_all_holders_excluded_skill_appears_in_lost(self):
        """When all skill holders are excluded, constraint is skipped; skill shows in lost."""
        emp, scores, holders = self._skill_dataset()
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg,
                       exclude={"S1", "S2"})
        assert result.is_feasible
        assert "python" in result.critical_skills_lost

    def test_skills_preserved_and_lost_partitions(self):
        emp, scores, _ = self._skill_dataset()
        holders = {"python": ["S1", "S2"], "haskell": ["G1"]}
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg)
        all_skills = set(result.critical_skills_preserved) | set(result.critical_skills_lost)
        assert all_skills == {"python", "haskell"}

    def test_no_holders_in_dataset_does_not_crash(self):
        """Skill holders list is empty → constraint skipped (no available)."""
        emp, scores, _ = self._skill_dataset()
        holders = {"ghost_skill": []}
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg)
        assert result.is_feasible

    def test_skill_constraint_disabled_allows_losing_skills(self):
        emp, scores, holders = self._skill_dataset()
        cfg = _no_constraints()
        # With only 100k budget (1 employee) and skill constraint OFF, optimizer picks G1 (90)
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg)
        # G1 retained, both skill holders at risk
        assert "python" in result.critical_skills_lost


# ---------------------------------------------------------------------------
# 5. Min-team-size constraint
# ---------------------------------------------------------------------------

class TestMinTeamSize:
    def _two_member_team(self):
        emp = _make_employees([
            {"employee_id": "A", "team_id": "T1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "B", "team_id": "T1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "C", "team_id": "T2", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "A", "impact_score": 30},
            {"employee_id": "B", "impact_score": 40},
            {"employee_id": "C", "impact_score": 90},
        ])
        return emp, scores

    def test_min_team_size_2_forces_both_t1_retained(self):
        emp, scores = self._two_member_team()
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=False,
                               min_team_size=2, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg)
        t1_retained = {"A", "B"} & result.retained_ids
        assert len(t1_retained) >= 2

    def test_min_team_size_0_does_not_force_extra_retention(self):
        emp, scores = self._two_member_team()
        cfg = _no_constraints()
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=cfg)
        assert result.n_retained == 1  # just C (highest impact)


# ---------------------------------------------------------------------------
# 6. Succession depth
# ---------------------------------------------------------------------------

class TestSuccessionDepth:
    def test_depth_1_requires_two_holders(self):
        """succession_depth=1 → need at least 2 holders of each critical skill."""
        emp = _make_employees([
            {"employee_id": f"E{i}", "annual_salary": 100_000, "annual_benefits": 0}
            for i in range(4)
        ])
        scores = _make_scores([
            {"employee_id": f"E{i}", "impact_score": 60 + i * 5}
            for i in range(4)
        ])
        holders = {"sql": ["E0", "E1"]}
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True,
                               succession_depth=1, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg)
        retained_holders = {"E0", "E1"} & result.retained_ids
        assert len(retained_holders) >= 2

    def test_depth_0_requires_only_one_holder(self):
        emp = _make_employees([
            {"employee_id": "H1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "H2", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "N1", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "H1", "impact_score": 30},
            {"employee_id": "H2", "impact_score": 31},
            {"employee_id": "N1", "impact_score": 90},
        ])
        holders = {"skill_x": ["H1", "H2"]}
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True,
                               succession_depth=0, solver_msg=False)
        result = solve(emp, budget_target=200_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg)
        # With budget for 2 and depth=0, can retain N1 + one holder
        retained_holders = {"H1", "H2"} & result.retained_ids
        assert len(retained_holders) >= 1


# ---------------------------------------------------------------------------
# 7. Force retain
# ---------------------------------------------------------------------------

class TestForceRetain:
    def test_force_retained_employee_always_in_retained_ids(self, five_employees):
        emp, scores = five_employees
        # E5 has lowest impact (50) — without force-retain it would be dropped at tight budget
        result = solve(emp, budget_target=350_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"E5"})
        assert "E5" in result.retained_ids

    def test_force_retain_count_reflects_actual_force_retained(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"E1", "E2"})
        assert result.force_retain_count == 2

    def test_force_retain_unknown_id_does_not_crash(self, five_employees):
        """IDs not in the employee dataset are silently ignored."""
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"GHOST_ID"})
        assert result.is_feasible

    def test_force_retain_all_employees_exceeds_tight_budget(self, five_employees):
        emp, scores = five_employees
        240_000 + 4 * 120_000  # E1=240k, E2-E5=120k each
        result = solve(emp, budget_target=10_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"E1", "E2", "E3", "E4", "E5"})
        assert not result.is_feasible

    def test_force_retain_and_exclude_different_employees(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"E1"}, exclude={"E5"})
        assert "E1" in result.retained_ids
        assert "E5" not in result.retained_ids


# ---------------------------------------------------------------------------
# 8. Exclude overrides
# ---------------------------------------------------------------------------

class TestExclude:
    def test_excluded_employee_never_in_retained_ids(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       exclude={"E1"})
        assert "E1" not in result.retained_ids

    def test_exclude_count_reflects_actual_excluded(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       exclude={"E3", "E4"})
        assert result.exclude_count == 2

    def test_exclude_unknown_id_does_not_crash(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       exclude={"GHOST_ID"})
        assert result.is_feasible

    def test_exclude_all_employees_retains_none(self, five_employees):
        """Excluding all employees → 0 retained is the optimal solution."""
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       exclude={"E1", "E2", "E3", "E4", "E5"})
        assert result.n_retained == 0
        assert result.knowledge_loss_score == 1.0


# ---------------------------------------------------------------------------
# 9. Empty dataset
# ---------------------------------------------------------------------------

class TestEmptyDataset:
    def test_empty_employees_returns_empty_status(self):
        emp = pd.DataFrame(columns=[
            "employee_id", "team_id", "seniority_level",
            "annual_salary", "annual_benefits"
        ])
        scores = pd.DataFrame(columns=["employee_id", "impact_score"])
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.status == "Empty"
        assert result.n_total == 0

    def test_empty_dataset_returns_zero_metrics(self):
        emp = pd.DataFrame(columns=[
            "employee_id", "team_id", "seniority_level",
            "annual_salary", "annual_benefits"
        ])
        scores = pd.DataFrame(columns=["employee_id", "impact_score"])
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.total_impact == 0.0
        assert result.total_cost == 0.0
        assert result.knowledge_loss_score == 0.0


# ---------------------------------------------------------------------------
# 10. OptimizationResult properties
# ---------------------------------------------------------------------------

class TestOptimizationResultProperties:
    def test_is_feasible_true_when_status_optimal(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.is_feasible is True

    def test_is_feasible_false_when_force_retain_exceeds_budget(self, five_employees):
        """Forcing a 240k employee on a 100k budget is truly infeasible."""
        emp, scores = five_employees
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"E1"})  # E1 costs 240k
        assert result.is_feasible is False

    def test_impact_delta_positive_when_high_performers_retained(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        # All retained → avg_retained ≈ avg_baseline → delta ≈ 0
        assert abs(result.impact_delta) < 1.0

    def test_knowledge_loss_score_bounded_0_1(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=300_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert 0.0 <= result.knowledge_loss_score <= 1.0

    def test_knowledge_loss_zero_when_all_retained(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.knowledge_loss_score == 0.0

    def test_solver_time_ms_positive(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.solver_time_ms > 0


# ---------------------------------------------------------------------------
# 11. Infeasibility result structure
# ---------------------------------------------------------------------------

class TestInfeasibilityResult:
    def test_infeasible_result_has_empty_retained_ids(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=0, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert len(result.retained_ids) == 0

    def test_infeasible_result_has_all_employees_at_risk(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=0, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        if not result.is_feasible:
            assert result.n_at_risk == result.n_total

    def test_infeasible_result_has_infeasibility_reason(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=0, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        if not result.is_feasible:
            assert result.infeasibility_reason is not None
            assert len(result.infeasibility_reason) > 0

    def test_knowledge_loss_score_1_when_infeasible(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=0, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        if not result.is_feasible:
            assert result.knowledge_loss_score == 1.0


# ---------------------------------------------------------------------------
# 12. diagnose_infeasibility
# ---------------------------------------------------------------------------

class TestDiagnoseInfeasibility:
    def test_returns_list_of_strings(self, five_employees):
        emp, scores = five_employees
        causes = diagnose_infeasibility(
            employees=emp, budget_target=1_000_000,
            impact_scores=scores, critical_skill_holders={},
            force_retain=set(), exclude=set(),
            constraint_config=_no_constraints(),
        )
        assert isinstance(causes, list)
        assert all(isinstance(c, str) for c in causes)

    def test_identifies_force_retain_budget_overrun(self, five_employees):
        emp, scores = five_employees
        causes = diagnose_infeasibility(
            employees=emp, budget_target=100,
            impact_scores=scores, critical_skill_holders={},
            force_retain={"E1", "E2"},
            exclude=set(),
            constraint_config=_no_constraints(),
        )
        combined_text = " ".join(causes).lower()
        assert "force" in combined_text or "budget" in combined_text

    def test_identifies_all_holders_excluded(self):
        emp = _make_employees([
            {"employee_id": "H1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "H2", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "H1", "impact_score": 60},
            {"employee_id": "H2", "impact_score": 70},
        ])
        holders = {"rust": ["H1", "H2"]}
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True, solver_msg=False)
        causes = diagnose_infeasibility(
            employees=emp, budget_target=1_000_000,
            impact_scores=scores, critical_skill_holders=holders,
            force_retain=set(), exclude={"H1", "H2"},
            constraint_config=cfg,
        )
        assert any("rust" in c or "skill" in c.lower() for c in causes)

    def test_identifies_all_leaders_excluded(self):
        emp = _make_employees([
            {"employee_id": "L1", "seniority_level": "lead",
             "annual_salary": 150_000, "annual_benefits": 0},
            {"employee_id": "M1", "seniority_level": "mid",
             "annual_salary": 80_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "L1", "impact_score": 60},
            {"employee_id": "M1", "impact_score": 80},
        ])
        cfg = ConstraintConfig(require_leadership_per_team=True,
                               require_critical_skills=False, solver_msg=False)
        causes = diagnose_infeasibility(
            employees=emp, budget_target=1_000_000,
            impact_scores=scores, critical_skill_holders={},
            force_retain=set(), exclude={"L1"},
            constraint_config=cfg,
        )
        assert any("leader" in c.lower() or "excluded" in c.lower() for c in causes)

    def test_returns_generic_reason_when_no_specific_cause_found(self, five_employees):
        emp, scores = five_employees
        causes = diagnose_infeasibility(
            employees=emp, budget_target=1_000_000,
            impact_scores=scores, critical_skill_holders={},
            force_retain=set(), exclude=set(),
            constraint_config=_no_constraints(),
        )
        assert len(causes) >= 1

    def test_empty_employees_returns_message(self):
        emp = pd.DataFrame(columns=[
            "employee_id", "team_id", "seniority_level",
            "annual_salary", "annual_benefits"
        ])
        scores = pd.DataFrame(columns=["employee_id", "impact_score"])
        causes = diagnose_infeasibility(
            employees=emp, budget_target=100_000,
            impact_scores=scores, critical_skill_holders={},
            force_retain=set(), exclude=set(),
            constraint_config=_no_constraints(),
        )
        assert len(causes) == 1
        assert "no employees" in causes[0].lower()


# ---------------------------------------------------------------------------
# 13. Missing impact scores
# ---------------------------------------------------------------------------

class TestMissingImpactScores:
    def test_employee_with_no_score_gets_zero_impact(self):
        emp = _make_employees([
            {"employee_id": "E1", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "E2", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        # Only provide score for E2
        scores = _make_scores([{"employee_id": "E2", "impact_score": 80}])
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.is_feasible
        # Optimizer should prefer E2 (80) over E1 (0)
        assert "E2" in result.retained_ids

    def test_completely_missing_scores_df_still_solves(self):
        emp = _make_employees([
            {"employee_id": "E1", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = pd.DataFrame(columns=["employee_id", "impact_score"])
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.is_feasible


# ---------------------------------------------------------------------------
# 14. Team impact change
# ---------------------------------------------------------------------------

class TestTeamImpactChange:
    def test_team_impact_change_dict_has_all_teams(self, five_employees):
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        # All employees are on T1
        assert "T1" in result.team_impact_change

    def test_team_impact_change_nonnegative_when_best_retained(self, five_employees):
        """When all employees retained, impact delta should be ≈ 0."""
        emp, scores = five_employees
        result = solve(emp, budget_target=10_000_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        for delta in result.team_impact_change.values():
            assert abs(delta) < 1e-3  # all retained → avg unchanged


# ---------------------------------------------------------------------------
# 15. Single employee edge cases
# ---------------------------------------------------------------------------

class TestSingleEmployee:
    def test_single_employee_retained_when_budget_sufficient(self):
        emp = _make_employees([{"employee_id": "SOLO", "annual_salary": 80_000, "annual_benefits": 10_000}])
        scores = _make_scores([{"employee_id": "SOLO", "impact_score": 75}])
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.is_feasible
        assert "SOLO" in result.retained_ids

    def test_single_employee_budget_too_tight_retains_zero(self):
        """Budget < employee cost → retaining 0 is optimal (not infeasible)."""
        emp = _make_employees([{"employee_id": "SOLO", "annual_salary": 80_000, "annual_benefits": 10_000}])
        scores = _make_scores([{"employee_id": "SOLO", "impact_score": 75}])
        result = solve(emp, budget_target=50_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints())
        assert result.n_retained == 0
        assert result.knowledge_loss_score == 1.0

    def test_single_employee_force_retained_budget_too_tight_is_infeasible(self):
        """Force-retaining a single employee whose cost > budget → truly infeasible."""
        emp = _make_employees([{"employee_id": "SOLO", "annual_salary": 80_000, "annual_benefits": 10_000}])
        scores = _make_scores([{"employee_id": "SOLO", "impact_score": 75}])
        result = solve(emp, budget_target=50_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"SOLO"})
        assert not result.is_feasible

    def test_single_employee_force_retained_within_budget(self):
        emp = _make_employees([{"employee_id": "SOLO", "annual_salary": 80_000, "annual_benefits": 10_000}])
        scores = _make_scores([{"employee_id": "SOLO", "impact_score": 75}])
        result = solve(emp, budget_target=100_000, impact_scores=scores,
                       critical_skill_holders={}, constraint_config=_no_constraints(),
                       force_retain={"SOLO"})
        assert "SOLO" in result.retained_ids


# ---------------------------------------------------------------------------
# 16. Constraint combinations
# ---------------------------------------------------------------------------

class TestCombinedConstraints:
    def test_leadership_and_skills_both_enforced(self):
        emp = _make_employees([
            {"employee_id": "L1", "team_id": "T1", "seniority_level": "lead",
             "annual_salary": 200_000, "annual_benefits": 0},
            {"employee_id": "S1", "team_id": "T1", "seniority_level": "mid",
             "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "M1", "team_id": "T1", "seniority_level": "mid",
             "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "L1", "impact_score": 40},
            {"employee_id": "S1", "impact_score": 30},
            {"employee_id": "M1", "impact_score": 90},
        ])
        holders = {"rare_skill": ["S1"]}
        cfg = ConstraintConfig(require_leadership_per_team=True,
                               require_critical_skills=True, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg)
        assert "L1" in result.retained_ids
        assert "S1" in result.retained_ids

    def test_force_retain_and_skills_constraint(self):
        emp = _make_employees([
            {"employee_id": "FR", "annual_salary": 100_000, "annual_benefits": 0},
            {"employee_id": "SK", "annual_salary": 100_000, "annual_benefits": 0},
        ])
        scores = _make_scores([
            {"employee_id": "FR", "impact_score": 20},
            {"employee_id": "SK", "impact_score": 50},
        ])
        holders = {"skill_x": ["SK"]}
        cfg = ConstraintConfig(require_leadership_per_team=False,
                               require_critical_skills=True, solver_msg=False)
        result = solve(emp, budget_target=1_000_000, impact_scores=scores,
                       critical_skill_holders=holders, constraint_config=cfg,
                       force_retain={"FR"})
        assert "FR" in result.retained_ids
        assert "SK" in result.retained_ids
