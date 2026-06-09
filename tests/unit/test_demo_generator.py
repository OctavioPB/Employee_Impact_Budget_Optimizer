"""Unit tests for the demo data generator (Sprint 1 DoD requirement)."""

import pandas as pd
import pytest

from demo_data.generator import DemoGenerator
from demo_data.scenarios import (
    ALL_SCENARIOS,
    SKILL_TAXONOMY,
    ScenarioConfig,
    get_headcount,
    load_scenario,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def small_a_org():
    """Small Scenario A org — generated once per module for speed."""
    gen = DemoGenerator("A", "small", seed=0)
    return gen.generate()


@pytest.fixture(scope="module")
def medium_b_org():
    gen = DemoGenerator("B", "medium", seed=1)
    return gen.generate()


@pytest.fixture(scope="module")
def small_c_org():
    gen = DemoGenerator("C", "small", seed=2)
    return gen.generate()


# ---------------------------------------------------------------------------
# Smoke tests — import and basic instantiation
# ---------------------------------------------------------------------------

class TestSmoke:
    def test_load_scenario_a(self):
        cfg = load_scenario("A")
        assert isinstance(cfg, ScenarioConfig)
        assert cfg.id == "A"

    def test_load_scenario_b(self):
        cfg = load_scenario("B")
        assert cfg.id == "B"

    def test_load_scenario_c(self):
        cfg = load_scenario("C")
        assert cfg.id == "C"

    def test_invalid_scenario_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            load_scenario("Z")

    def test_invalid_size_raises(self):
        with pytest.raises(ValueError, match="Unknown org size"):
            get_headcount("xlarge")

    def test_generator_instantiation(self):
        gen = DemoGenerator("A", "small", seed=42)
        assert gen.target_headcount == 50
        assert gen.org_size == "small"

    def test_skill_taxonomy_not_empty(self):
        assert len(SKILL_TAXONOMY) > 10

    def test_all_scenarios_loadable(self):
        for sid in ALL_SCENARIOS:
            cfg = load_scenario(sid)
            assert cfg.departments


# ---------------------------------------------------------------------------
# Generated org structure
# ---------------------------------------------------------------------------

class TestOrgStructure:
    def test_generate_returns_all_dataframes(self, small_a_org):
        org = small_a_org
        assert isinstance(org.teams, pd.DataFrame)
        assert isinstance(org.employees, pd.DataFrame)
        assert isinstance(org.performance, pd.DataFrame)
        assert isinstance(org.skills, pd.DataFrame)
        assert isinstance(org.employee_skills, pd.DataFrame)
        assert isinstance(org.collaboration, pd.DataFrame)
        assert isinstance(org.budget, pd.DataFrame)

    def test_org_has_correct_metadata(self, small_a_org):
        assert small_a_org.scenario_id == "A"
        assert small_a_org.org_size == "small"
        assert small_a_org.industry != ""
        assert small_a_org.org_name != ""


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

class TestEmployees:
    def test_headcount_approximately_correct(self, small_a_org):
        target = get_headcount("small")  # 50
        actual = len(small_a_org.employees)
        # Allow ±15% for rounding across departments
        assert abs(actual - target) / target <= 0.15, (
            f"Headcount {actual} too far from target {target}"
        )

    def test_medium_org_headcount(self, medium_b_org):
        target = get_headcount("medium")  # 500
        actual = len(medium_b_org.employees)
        assert abs(actual - target) / target <= 0.15

    def test_required_columns_present(self, small_a_org):
        required = {
            "employee_id", "full_name", "role_title", "seniority_level",
            "department", "team_id", "hire_date", "annual_salary", "annual_benefits",
        }
        assert required <= set(small_a_org.employees.columns)

    def test_no_null_employee_ids(self, small_a_org):
        assert small_a_org.employees["employee_id"].notna().all()

    def test_employee_ids_unique(self, small_a_org):
        assert small_a_org.employees["employee_id"].is_unique

    def test_salaries_positive(self, small_a_org):
        assert (small_a_org.employees["annual_salary"] > 0).all()

    def test_salary_range_realistic(self, small_a_org):
        lo, hi = 30_000, 1_000_000
        assert (small_a_org.employees["annual_salary"] >= lo).all()
        assert (small_a_org.employees["annual_salary"] <= hi).all()

    def test_benefits_approx_30pct(self, small_a_org):
        ratio = (
            small_a_org.employees["annual_benefits"]
            / small_a_org.employees["annual_salary"]
        )
        # Generator sets benefits at 30%; allow ±5%
        assert (ratio.between(0.25, 0.35)).all()

    def test_seniority_levels_valid(self, small_a_org):
        valid = {"junior", "mid", "senior", "lead", "director", "exec"}
        actual = set(small_a_org.employees["seniority_level"].unique())
        assert actual <= valid, f"Invalid seniority values: {actual - valid}"

    def test_all_employees_have_team(self, small_a_org):
        assert small_a_org.employees["team_id"].notna().all()

    def test_team_ids_reference_dim_team(self, small_a_org):
        valid_teams = set(small_a_org.teams["team_id"])
        emp_teams = set(small_a_org.employees["team_id"])
        assert emp_teams <= valid_teams

    def test_departments_cover_scenario_config(self, small_a_org):
        cfg = load_scenario("A")
        expected_depts = {d["name"] for d in cfg.departments}
        actual_depts = set(small_a_org.employees["department"].unique())
        assert actual_depts <= expected_depts or actual_depts == expected_depts

    def test_reproducibility_with_same_seed(self):
        gen1 = DemoGenerator("A", "small", seed=99)
        gen2 = DemoGenerator("A", "small", seed=99)
        org1 = gen1.generate()
        org2 = gen2.generate()
        assert org1.employees["employee_id"].tolist() == org2.employees["employee_id"].tolist()

    def test_different_seeds_produce_different_data(self):
        org1 = DemoGenerator("A", "small", seed=1).generate()
        org2 = DemoGenerator("A", "small", seed=2).generate()
        # Different seeds should produce different employee IDs
        assert org1.employees["employee_id"].tolist() != org2.employees["employee_id"].tolist()


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TestTeams:
    def test_teams_not_empty(self, small_a_org):
        assert len(small_a_org.teams) > 0

    def test_team_columns_present(self, small_a_org):
        required = {"team_id", "team_name", "department", "annual_budget"}
        assert required <= set(small_a_org.teams.columns)

    def test_team_budgets_positive(self, small_a_org):
        assert (small_a_org.teams["annual_budget"] > 0).all()

    def test_team_ids_unique(self, small_a_org):
        assert small_a_org.teams["team_id"].is_unique


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_performance_not_empty(self, small_a_org):
        assert len(small_a_org.performance) > 0

    def test_kpi_scores_in_range(self, small_a_org):
        kpi = small_a_org.performance["kpi_score"]
        assert (kpi >= 1.0).all() and (kpi <= 5.0).all()

    def test_all_employees_have_performance(self, small_a_org):
        emp_ids = set(small_a_org.employees["employee_id"])
        perf_ids = set(small_a_org.performance["employee_id"])
        assert perf_ids <= emp_ids
        # At least 80% of employees have at least one review
        coverage = len(perf_ids & emp_ids) / len(emp_ids)
        assert coverage >= 0.80

    def test_review_periods_format(self, small_a_org):
        import re
        pattern = re.compile(r"^\d{4}-Q[1-4]$")
        for period in small_a_org.performance["review_period"].unique():
            assert pattern.match(period), f"Bad period format: {period}"

    def test_goals_met_pct_in_range(self, small_a_org):
        pct = small_a_org.performance["goals_met_pct"]
        assert (pct >= 0).all() and (pct <= 100).all()


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

class TestSkills:
    def test_skills_cover_taxonomy(self, small_a_org):
        assert len(small_a_org.skills) == len(SKILL_TAXONOMY)

    def test_skill_columns_present(self, small_a_org):
        required = {"skill_id", "skill_name", "category", "is_critical", "market_scarcity"}
        assert required <= set(small_a_org.skills.columns)

    def test_market_scarcity_range(self, small_a_org):
        scarcity = small_a_org.skills["market_scarcity"]
        assert (scarcity >= 0).all() and (scarcity <= 1).all()

    def test_employee_skills_not_empty(self, small_a_org):
        assert len(small_a_org.employee_skills) > 0

    def test_employee_skills_proficiency_range(self, small_a_org):
        prof = small_a_org.employee_skills["proficiency"]
        assert (prof >= 0).all() and (prof <= 1).all()

    def test_each_employee_has_at_least_one_skill(self, small_a_org):
        emp_ids = set(small_a_org.employees["employee_id"])
        skilled_ids = set(small_a_org.employee_skills["employee_id"])
        # At least 90% of employees have at least one skill
        coverage = len(emp_ids & skilled_ids) / len(emp_ids)
        assert coverage >= 0.90


# ---------------------------------------------------------------------------
# Collaboration network
# ---------------------------------------------------------------------------

class TestCollaboration:
    def test_collaboration_not_empty(self, small_a_org):
        assert len(small_a_org.collaboration) > 0

    def test_relationship_types_valid(self, small_a_org):
        valid = {"collaborates_with", "reports_to", "mentors"}
        actual = set(small_a_org.collaboration["relationship_type"].unique())
        assert actual <= valid

    def test_interaction_weights_in_range(self, small_a_org):
        w = small_a_org.collaboration["interaction_weight"]
        assert (w >= 0).all() and (w <= 1).all()

    def test_no_self_loops(self, small_a_org):
        df = small_a_org.collaboration
        self_loops = df[df["source_id"] == df["target_id"]]
        assert len(self_loops) == 0

    def test_reports_to_edges_present(self, small_a_org):
        reports = small_a_org.collaboration[
            small_a_org.collaboration["relationship_type"] == "reports_to"
        ]
        assert len(reports) > 0

    def test_collaboration_references_valid_employees(self, small_a_org):
        emp_ids = set(small_a_org.employees["employee_id"])
        sources = set(small_a_org.collaboration["source_id"])
        targets = set(small_a_org.collaboration["target_id"])
        assert sources <= emp_ids
        assert targets <= emp_ids


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class TestBudget:
    def test_budget_not_empty(self, small_a_org):
        assert len(small_a_org.budget) > 0

    def test_budget_columns_present(self, small_a_org):
        required = {
            "budget_id", "team_id", "fiscal_period",
            "budgeted_amount", "actual_amount",
        }
        assert required <= set(small_a_org.budget.columns)

    def test_budget_amounts_positive(self, small_a_org):
        assert (small_a_org.budget["budgeted_amount"] > 0).all()
        assert (small_a_org.budget["actual_amount"] > 0).all()

    def test_over_budget_scenario_has_variance(self, small_a_org):
        """Scenario A should have some teams over budget."""
        df = small_a_org.budget
        variance = df["actual_amount"] - df["budgeted_amount"]
        # At least some quarters should be over budget in Scenario A
        assert (variance > 0).any()


# ---------------------------------------------------------------------------
# All scenarios × sizes smoke test
# ---------------------------------------------------------------------------

class TestAllCombinations:
    @pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
    @pytest.mark.parametrize("org_size", ["small"])  # small for speed in CI
    def test_generate_completes_without_error(self, scenario_id, org_size):
        gen = DemoGenerator(scenario_id, org_size, seed=42)
        org = gen.generate()
        assert len(org.employees) > 0
        assert len(org.teams) > 0
        assert len(org.performance) > 0

    @pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
    def test_scenarios_have_unique_challenges(self, scenario_id):
        cfg = load_scenario(scenario_id)
        assert len(cfg.challenges) >= 2
        assert cfg.total_budget_variance > 1.0
