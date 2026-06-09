"""Unit tests for strategic_planner modules.

Covers: FutureStateAnalyzer, SkillsGapAnalyzer, TransitionPlanner,
        StrategyComparator (all four Sprint 6 modules).
"""

from __future__ import annotations

import pandas as pd
import pytest

from strategic_planner.future_state import (
    FutureStateAnalyzer,
    FutureStateDesign,
    ProposedRole,
    analyze_future_state,
    build_demo_design,
)
from strategic_planner.skills_gap import (
    SkillRequirement,
    SkillsGapAnalysis,
    SkillsGapAnalyzer,
    analyze_skills_gap,
    build_demo_requirements,
)
from strategic_planner.strategy_comparator import (
    PRESET_STRATEGIES,
    ComparisonResult,
    StrategyComparator,
    WorkforceStrategy,
    compare_strategies,
)
from strategic_planner.transition_planner import (
    TransitionPlan,
    TransitionPlanner,
    plan_transition,
)

# ===========================================================================
# Shared fixtures
# ===========================================================================

@pytest.fixture
def small_employees() -> pd.DataFrame:
    return pd.DataFrame({
        "employee_id": ["E1", "E2", "E3", "E4", "E5"],
        "full_name":   ["Alice", "Bob", "Carol", "Dave", "Eve"],
        "role_title":  ["Engineer", "Engineer", "Analyst", "Manager", "Engineer"],
        "seniority_level": ["senior", "mid", "mid", "lead", "junior"],
        "annual_salary":   [130_000, 90_000, 85_000, 160_000, 65_000],
        "department":      ["Engineering", "Engineering", "Analytics", "Engineering", "Engineering"],
    })


@pytest.fixture
def skills_df() -> pd.DataFrame:
    return pd.DataFrame({
        "skill_id":   ["S1", "S2", "S3", "S4", "S5"],
        "skill_name": ["python", "sql", "machine_learning", "aws", "tableau"],
        "category":   ["Engineering", "Data", "Data", "Cloud", "Analytics"],
        "is_critical": [True, False, True, False, False],
    })


@pytest.fixture
def employee_skills_df() -> pd.DataFrame:
    # E1: python + aws | E2: python + sql | E3: sql + tableau | E4: python | E5: sql
    return pd.DataFrame({
        "employee_id": ["E1", "E1", "E2", "E2", "E3", "E3", "E4", "E5"],
        "skill_id":    ["S1", "S4", "S1", "S2", "S2", "S5", "S1", "S2"],
        "proficiency": [4, 3, 3, 4, 5, 3, 3, 2],
        "is_primary":  [True, False, True, True, True, True, True, True],
    })


# ===========================================================================
# 1. FutureStateAnalyzer
# ===========================================================================

class TestFutureStateDesign:
    def test_total_proposed_headcount(self):
        design = FutureStateDesign(
            name="Test",
            description="",
            proposed_teams={
                "Eng": [ProposedRole("SWE", "senior", count=3),
                        ProposedRole("QA",  "mid",    count=2)],
                "PM":  [ProposedRole("PM",  "mid",    count=1)],
            },
        )
        assert design.total_proposed_headcount == 6

    def test_unique_role_count(self):
        design = FutureStateDesign(
            name="Test",
            description="",
            proposed_teams={
                "Eng": [ProposedRole("SWE", "senior"), ProposedRole("QA", "mid")],
            },
        )
        assert design.unique_role_count == 2

    def test_seniority_normalised_to_lower(self):
        role = ProposedRole("Staff Eng", "SENIOR", ["python"])
        assert role.seniority_level == "senior"


class TestFutureStateAnalyzer:
    def _make_design(self, count: int = 2) -> FutureStateDesign:
        return FutureStateDesign(
            name="Target",
            description="Test design",
            proposed_teams={
                "Engineering": [
                    ProposedRole("Senior Engineer", "senior", ["python", "aws"], count=count),
                ],
            },
            annual_budget_envelope=5_000_000,
        )

    def test_returns_future_state_analysis(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design()
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        assert result is not None

    def test_estimated_annual_cost_positive(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design()
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        assert result.estimated_annual_cost > 0

    def test_salary_auto_filled_when_zero(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design()
        FutureStateAnalyzer()._fill_salary_estimates(design)
        for roles in design.proposed_teams.values():
            for role in roles:
                assert role.estimated_salary > 0

    def test_internal_fills_not_exceed_headcount(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design(count=2)
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        # Internal fills per role cannot exceed count
        assert result.n_internal_fills <= 2

    def test_internal_fill_rate_between_0_and_1(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design()
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        assert 0.0 <= result.internal_fill_rate <= 1.0

    def test_delta_vs_current_computed(self, small_employees, employee_skills_df, skills_df):
        current_spend = 500_000.0
        design = self._make_design()
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df,
            current_total_spend=current_spend,
        )
        assert result.delta_vs_current == pytest.approx(
            result.estimated_annual_cost - current_spend, rel=1e-6
        )

    def test_budget_feasible_flag(self, small_employees, employee_skills_df, skills_df):
        # Budget envelope larger than estimated cost → feasible
        design = FutureStateDesign(
            name="Small",
            description="",
            proposed_teams={"Eng": [ProposedRole("Dev", "junior", count=1)]},
            annual_budget_envelope=10_000_000,
        )
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        assert result.budget_feasible is True

    def test_budget_infeasible_adds_warning(self, small_employees, employee_skills_df, skills_df):
        design = FutureStateDesign(
            name="Expensive",
            description="",
            proposed_teams={
                "Exec": [ProposedRole("VP Eng", "vp", count=10)]
            },
            annual_budget_envelope=100,
        )
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        assert not result.budget_feasible
        assert len(result.warnings) > 0

    def test_months_to_target_positive(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design()
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        assert result.months_to_target >= 1

    def test_summary_df_has_required_columns(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design()
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df
        )
        df = result.summary_df()
        for col in ["team", "role", "seniority", "count", "est_salary", "team_cost"]:
            assert col in df.columns

    def test_empty_employees_handled_gracefully(self, skills_df):
        design = self._make_design()
        result = FutureStateAnalyzer().analyze(
            design,
            pd.DataFrame(),
            pd.DataFrame(),
            skills_df,
        )
        assert result is not None
        assert result.n_internal_fills == 0

    def test_severance_zero_when_no_reduction(self, small_employees, employee_skills_df, skills_df):
        # Proposed headcount same as current → no severance
        design = FutureStateDesign(
            name="Same size",
            description="",
            proposed_teams={
                "Eng": [ProposedRole("Eng", "mid", count=len(small_employees))]
            },
        )
        result = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df,
            current_total_spend=530_000,
        )
        assert result.severance_cost == 0.0

    def test_build_demo_design_returns_valid_design(self):
        for size in ("small", "medium", "large"):
            d = build_demo_design(org_size=size)
            assert d.total_proposed_headcount > 0
            assert d.annual_budget_envelope > 0

    def test_analyze_future_state_convenience_wrapper(self, small_employees, employee_skills_df, skills_df):
        design = self._make_design()
        result = analyze_future_state(design, small_employees, employee_skills_df, skills_df)
        assert result is not None


# ===========================================================================
# 2. SkillsGapAnalyzer
# ===========================================================================

class TestSkillsGapAnalyzer:
    def _make_requirements(self) -> list[SkillRequirement]:
        return [
            SkillRequirement("python",          3, 3, 12, is_critical=True),
            SkillRequirement("machine_learning", 4, 2, 12, is_critical=True),
            SkillRequirement("sql",              2, 4, 12, is_critical=False),
            SkillRequirement("tableau",          2, 1, 12, is_critical=False),
        ]

    def test_returns_skills_gap_analysis(self, small_employees, employee_skills_df, skills_df):
        reqs = self._make_requirements()
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert isinstance(result, SkillsGapAnalysis)

    def test_gap_count_matches_requirements(self, small_employees, employee_skills_df, skills_df):
        reqs = self._make_requirements()
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert len(result.gaps) == len(reqs)

    def test_gap_df_has_required_columns(self, small_employees, employee_skills_df, skills_df):
        reqs = self._make_requirements()
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        df = result.gap_df
        for col in ["skill", "required", "current", "gap", "severity", "recommendation"]:
            assert col in df.columns

    def test_severity_covered_when_no_gap(self, small_employees, employee_skills_df, skills_df):
        # All 3 holders of python exist (E1, E2, E4) and requirement is 3 → covered
        reqs = [SkillRequirement("python", 3, 3, 12)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        gap = result.gaps[0]
        assert gap.gap >= 0
        assert gap.severity == "Covered"

    def test_severity_critical_for_critical_skill_with_gap(self, small_employees, employee_skills_df, skills_df):
        # machine_learning: 0 holders, required 2, is_critical=True → Critical
        reqs = [SkillRequirement("machine_learning", 4, 2, 12, is_critical=True)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].severity == "Critical"

    def test_severity_moderate_for_single_gap_non_critical(self, small_employees, employee_skills_df, skills_df):
        # sql: E2, E3, E5 = 3 holders; required 4 → gap=-1, non-critical → Moderate
        reqs = [SkillRequirement("sql", 2, 4, 12, is_critical=False)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].severity == "Moderate"

    def test_coverage_pct_correct(self, small_employees, employee_skills_df, skills_df):
        # python: 3 holders, required 3 → 100%
        reqs = [SkillRequirement("python", 3, 3, 12)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].coverage_pct == pytest.approx(100.0)

    def test_build_cost_zero_when_covered(self, small_employees, employee_skills_df, skills_df):
        reqs = [SkillRequirement("python", 3, 3, 12)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].build_cost_total == 0.0

    def test_build_cost_positive_when_gap(self, small_employees, employee_skills_df, skills_df):
        reqs = [SkillRequirement("machine_learning", 4, 2, 12, is_critical=True)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].build_cost_total > 0

    def test_buy_cost_positive_when_gap(self, small_employees, employee_skills_df, skills_df):
        reqs = [SkillRequirement("machine_learning", 4, 2, 12, is_critical=True)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].buy_cost_total > 0

    def test_recommendation_covered_when_no_gap(self, small_employees, employee_skills_df, skills_df):
        reqs = [SkillRequirement("python", 3, 1, 12)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].recommendation == "Covered"

    def test_recommendation_buy_when_urgent_and_training_too_long(self, small_employees, employee_skills_df, skills_df):
        # horizon=3 months, ml training takes 6 months → Buy
        reqs = [SkillRequirement("machine_learning", 4, 2, 3, is_critical=True)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.gaps[0].recommendation == "Buy"

    def test_totals_are_non_negative(self, small_employees, employee_skills_df, skills_df):
        reqs = self._make_requirements()
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.total_build_cost >= 0
        assert result.total_buy_cost >= 0
        assert result.total_hybrid_cost >= 0

    def test_n_critical_gaps_count(self, small_employees, employee_skills_df, skills_df):
        reqs = self._make_requirements()
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.n_critical_gaps >= 0
        assert result.n_critical_gaps <= len(reqs)

    def test_n_covered_count(self, small_employees, employee_skills_df, skills_df):
        reqs = self._make_requirements()
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        assert result.n_covered >= 0

    def test_adjacency_candidates_list(self, small_employees, employee_skills_df, skills_df):
        # machine_learning adjacency includes python — E1, E2, E4 have python
        reqs = [SkillRequirement("machine_learning", 4, 2, 12, is_critical=True)]
        result = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        gap = result.gaps[0]
        assert isinstance(gap.adjacency_candidates, list)

    def test_empty_employees_handled(self, skills_df):
        reqs = [SkillRequirement("python", 3, 2, 12)]
        result = SkillsGapAnalyzer().analyze(
            reqs, pd.DataFrame(), pd.DataFrame(), skills_df
        )
        assert result is not None
        assert result.gaps[0].current_holders == 0

    def test_build_demo_requirements_returns_list(self, small_employees, skills_df):
        reqs = build_demo_requirements(small_employees, skills_df)
        assert isinstance(reqs, list)
        assert len(reqs) > 0

    def test_analyze_skills_gap_convenience_wrapper(self, small_employees, employee_skills_df, skills_df):
        reqs = self._make_requirements()
        result = analyze_skills_gap(reqs, small_employees, employee_skills_df, skills_df)
        assert isinstance(result, SkillsGapAnalysis)


# ===========================================================================
# 3. TransitionPlanner
# ===========================================================================

class TestTransitionPlanner:
    def _make_inputs(self, small_employees, employee_skills_df, skills_df):
        from strategic_planner.future_state import FutureStateAnalyzer
        from strategic_planner.skills_gap import SkillsGapAnalyzer

        design = FutureStateDesign(
            name="Target",
            description="",
            proposed_teams={"Eng": [ProposedRole("Dev", "mid", count=4)]},
        )
        fsa = FutureStateAnalyzer().analyze(
            design, small_employees, employee_skills_df, skills_df, current_total_spend=530_000
        )
        reqs = [
            SkillRequirement("python", 3, 3, 12, is_critical=True),
            SkillRequirement("sql",    2, 2, 12, is_critical=False),
        ]
        sga = SkillsGapAnalyzer().analyze(reqs, small_employees, employee_skills_df, skills_df)
        return fsa, sga

    def test_returns_transition_plan(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert isinstance(plan, TransitionPlan)

    def test_three_phases(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert len(plan.phases) == 3

    def test_phases_in_order(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        starts = [p.months_start for p in plan.phases]
        assert starts == sorted(starts)

    def test_total_months_positive(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert plan.total_months > 0

    def test_total_transition_cost_non_negative(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert plan.total_transition_cost >= 0

    def test_productivity_dip_between_0_and_40(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert 0.0 <= plan.productivity_dip_pct <= 40.0

    def test_knowledge_loss_risk_valid_string(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert plan.knowledge_loss_risk in ("Low", "Moderate", "High", "Critical")

    def test_risk_register_non_empty(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert len(plan.risks) > 0

    def test_gantt_df_has_required_columns(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        df = plan.gantt_df
        # gantt_df columns: phase, start, end, cost, risk, n_actions
        for col in ["phase", "start", "end", "risk", "n_actions"]:
            assert col in df.columns

    def test_action_df_has_required_columns(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        df = plan.action_df
        # action_df columns: phase, type, description, owner, cost, duration_weeks, priority
        for col in ["phase", "type", "owner", "priority", "duration_weeks"]:
            assert col in df.columns

    def test_executive_summary_non_empty(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        plan = TransitionPlanner().plan(fsa, sga, small_employees)
        assert len(plan.executive_summary) > 10

    def test_plan_transition_convenience_wrapper(self, small_employees, employee_skills_df, skills_df):
        fsa, sga = self._make_inputs(small_employees, employee_skills_df, skills_df)
        # plan_transition accepts employees_df as optional (defaults to empty DataFrame)
        plan = plan_transition(fsa, sga, current_employees_df=small_employees)
        assert isinstance(plan, TransitionPlan)


# ===========================================================================
# 4. StrategyComparator
# ===========================================================================

class TestWorkforceStrategy:
    def test_priorities_normalised(self):
        s = WorkforceStrategy(
            name="Test",
            description="",
            retention_priority=2.0,
            growth_priority=2.0,
            optimization_priority=6.0,
        )
        total = s.retention_priority + s.growth_priority + s.optimization_priority
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_zero_priorities_do_not_crash(self):
        # All zero priorities → __post_init__ skips normalisation
        s = WorkforceStrategy(
            name="Zero",
            description="",
            retention_priority=0.0,
            growth_priority=0.0,
            optimization_priority=0.0,
        )
        assert s is not None

    def test_preset_strategies_count(self):
        assert len(PRESET_STRATEGIES) == 4

    def test_preset_strategy_names_unique(self):
        names = [s.name for s in PRESET_STRATEGIES]
        assert len(names) == len(set(names))


class TestStrategyComparator:
    def _run(self, priorities=None) -> ComparisonResult:
        return compare_strategies(
            current_annual_spend=5_000_000,
            n_employees=100,
            avg_impact_score=60.0,
            n_nexus=5,
            attrition_rate=0.12,
            org_priorities=priorities,
        )

    def test_returns_comparison_result(self):
        result = self._run()
        assert isinstance(result, ComparisonResult)

    def test_scores_count_equals_strategies(self):
        result = self._run()
        assert len(result.scores) == len(PRESET_STRATEGIES)

    def test_ranks_are_unique(self):
        result = self._run()
        ranks = [s.rank for s in result.scores]
        assert sorted(ranks) == list(range(1, len(PRESET_STRATEGIES) + 1))

    def test_winner_has_rank_1(self):
        result = self._run()
        assert result.winner.rank == 1

    def test_recommended_strategy_name_in_scores(self):
        result = self._run()
        names = [s.strategy_name for s in result.scores]
        assert result.recommended_strategy in names

    def test_overall_scores_between_0_and_100(self):
        result = self._run()
        for s in result.scores:
            assert 0 <= s.overall_score <= 100

    def test_sub_scores_between_0_and_100(self):
        result = self._run()
        for s in result.scores:
            for attr in ("cost_score", "retention_score", "innovation_score",
                         "resilience_score", "speed_score"):
                val = getattr(s, attr)
                assert 0 <= val <= 100, f"{attr}={val} out of range"

    def test_two_year_cost_positive(self):
        result = self._run()
        for s in result.scores:
            assert s.two_year_cost > 0

    def test_retention_rate_between_0_and_1(self):
        result = self._run()
        for s in result.scores:
            assert 0 <= s.retention_rate_projection <= 1

    def test_innovation_score_between_0_and_100(self):
        result = self._run()
        for s in result.scores:
            assert 0 <= s.innovation_capacity_score <= 100

    def test_resilience_score_between_0_and_100(self):
        result = self._run()
        for s in result.scores:
            assert 0 <= s.operational_resilience_score <= 100

    def test_months_to_execute_positive(self):
        result = self._run()
        for s in result.scores:
            assert s.months_to_execute > 0

    def test_narrative_fields_populated(self):
        result = self._run()
        for s in result.scores:
            assert len(s.recommendation) > 0
            assert isinstance(s.strengths, list)
            assert isinstance(s.weaknesses, list)

    def test_radar_df_has_strategy_column(self):
        result = self._run()
        assert "Strategy" in result.radar_df.columns

    def test_radar_df_row_count(self):
        result = self._run()
        assert len(result.radar_df) == len(PRESET_STRATEGIES)

    def test_comparison_df_has_rank_column(self):
        result = self._run()
        assert "Rank" in result.comparison_df.columns

    def test_custom_org_priorities_normalised(self):
        comparator = StrategyComparator({"cost": 10, "retention": 0, "innovation": 0,
                                         "resilience": 0, "speed": 0})
        assert comparator._priorities["cost"] == pytest.approx(1.0, abs=1e-6)

    def test_cost_heavy_priority_favours_low_cost_strategy(self):
        # With 100% cost weight, the strategy with lowest 2-year cost should win
        result = self._run(priorities={"cost": 1, "retention": 0,
                                        "innovation": 0, "resilience": 0, "speed": 0})
        winner = result.winner
        all_costs = [s.two_year_cost for s in result.scores]
        assert winner.two_year_cost == min(all_costs)

    def test_retention_heavy_priority_favours_high_retention(self):
        result = self._run(priorities={"cost": 0, "retention": 1,
                                        "innovation": 0, "resilience": 0, "speed": 0})
        winner = result.winner
        all_retentions = [s.retention_rate_projection for s in result.scores]
        assert winner.retention_rate_projection == max(all_retentions)

    def test_custom_strategies(self):
        custom = [
            WorkforceStrategy("A", "Strategy A", budget_change_pct=-0.10,
                              retention_priority=0.5, growth_priority=0.3,
                              optimization_priority=0.2),
            WorkforceStrategy("B", "Strategy B", budget_change_pct=0.05,
                              retention_priority=0.7, growth_priority=0.2,
                              optimization_priority=0.1),
        ]
        result = compare_strategies(
            strategies=custom,
            current_annual_spend=2_000_000,
            n_employees=40,
        )
        assert len(result.scores) == 2
        assert result.winner.rank == 1

    def test_generated_at_non_empty(self):
        result = self._run()
        assert len(result.generated_at) > 0

    def test_org_priorities_sum_to_1(self):
        result = self._run()
        total = sum(result.org_priorities.values())
        assert total == pytest.approx(1.0, abs=1e-6)
