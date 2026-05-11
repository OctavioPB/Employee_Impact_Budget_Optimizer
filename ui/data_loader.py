"""Unified data loading layer for EIBO dashboard.

Demo mode:  generates data in-memory via DemoGenerator (no PostgreSQL needed).
Real mode:  reads from DuckDB gold layer (requires data pipeline to have run).

All results are cached with st.cache_data keyed on (demo_mode, scenario_id, size).
"""

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class DashboardData:
    """All pre-computed data the executive dashboard needs."""

    # --- raw tables (filtered to active employees) ---
    employees: pd.DataFrame
    """employee_id, full_name, role_title, department, team_id, seniority_level,
    annual_salary, annual_benefits, hire_date, location"""

    teams: pd.DataFrame
    """team_id, team_name, department, annual_budget"""

    performance: pd.DataFrame
    """employee_id, kpi_score, review_date, review_period"""

    skills: pd.DataFrame
    """skill_id, skill_name, category, is_critical, market_scarcity"""

    employee_skills: pd.DataFrame
    """employee_id, skill_id, proficiency, is_primary"""

    # --- impact & network ---
    impact_scores: pd.DataFrame
    """employee_id, impact_score, kpi_contribution, network_contribution,
    skills_contribution, cost_contribution, confidence"""

    centrality: pd.DataFrame
    """employee_id, degree_centrality, betweenness_centrality,
    eigenvector_centrality, pagerank, combined_centrality"""

    nexus_ids: set[str]
    communities: dict[str, int]  # employee_id → community_id
    team_fragility: dict[str, float]  # team_id → fragility [0, 1]

    # --- aggregated views ---
    dept_summary: pd.DataFrame
    """department, headcount, total_spend, annual_budget, budget_variance_pct,
    avg_impact, avg_kpi, fragility_avg"""

    team_summary: pd.DataFrame
    """team_id, team_name, department, headcount, total_spend, annual_budget,
    budget_variance_pct, avg_impact, fragility"""

    quarterly_spend: pd.DataFrame
    """fiscal_period, total_budgeted, total_actual, period_start"""

    quarterly_kpi: pd.DataFrame
    """review_period, avg_kpi, n_reviews"""

    # --- enriched employee table (for display) ---
    employee_table: pd.DataFrame
    """Denormalized view: employee + impact + is_nexus + top_skill + community"""

    # --- org-level KPIs ---
    total_headcount: int = 0
    total_spend: float = 0.0
    total_budget: float = 0.0
    avg_impact_score: float = 0.0
    budget_variance_pct: float = 0.0
    n_at_risk_teams: int = 0
    n_nexus_employees: int = 0
    org_name: str = ""
    scenario_id: str = ""
    org_size: str = ""

    graph_density: float = 0.0
    n_components: int = 0

    scoring_mode: str = "heuristic"


# ---------------------------------------------------------------------------
# Main loading function
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=3600)
def load_dashboard_data(
    demo_mode: bool,
    scenario_id: str,
    size: str,
) -> DashboardData:
    """Load and compute all dashboard data.

    Caches by (demo_mode, scenario_id, size) for 1 hour.
    """
    if demo_mode:
        return _load_demo(scenario_id, size)
    return _load_real()


# ---------------------------------------------------------------------------
# Demo loader
# ---------------------------------------------------------------------------

def _load_demo(scenario_id: str, size: str) -> DashboardData:
    """Generate synthetic org data and compute all derived metrics."""
    from demo_data.generator import DemoGenerator
    from models.impact_scorer import compute_impact_scores
    from models.network_analysis import analyze_network

    logger.info("Loading demo data: scenario=%s size=%s", scenario_id, size)

    gen = DemoGenerator(scenario_id, size)
    org = gen.generate()

    employees = org.employees.copy()
    # Drop internal generator column
    if "_is_nexus" in employees.columns:
        employees = employees.drop(columns=["_is_nexus"])

    performance = org.performance.copy()
    skills = org.skills.copy()
    employee_skills = org.employee_skills.copy()
    teams = org.teams.copy()
    collaboration = org.collaboration.copy()
    budget_df = org.budget.copy()

    # Network analysis
    net = analyze_network(collaboration, employees)

    # Impact scoring
    scoring_result = compute_impact_scores(
        employees_df=employees,
        performance_df=performance,
        centrality_df=net.centrality,
        employee_skills_df=employee_skills,
        skills_df=skills,
    )

    # Aggregations
    dept_summary = _build_dept_summary(
        employees, teams, scoring_result.scores, net.team_fragility
    )
    team_summary = _build_team_summary(
        employees, teams, scoring_result.scores, net.team_fragility
    )
    quarterly_spend = _build_quarterly_spend(budget_df)
    quarterly_kpi = _build_quarterly_kpi(performance)
    employee_table = _build_employee_table(
        employees, scoring_result.scores, net.nexus_ids,
        net.communities, employee_skills, skills
    )

    # Org-level KPIs
    total_spend = float(
        (employees["annual_salary"] + employees["annual_benefits"]).sum()
    )
    total_budget = float(teams["annual_budget"].sum())
    variance_pct = (total_spend - total_budget) / total_budget * 100 if total_budget > 0 else 0.0
    avg_impact = float(scoring_result.scores["impact_score"].mean())
    n_at_risk = int((dept_summary["budget_variance_pct"] > 10).sum())

    return DashboardData(
        employees=employees,
        teams=teams,
        performance=performance,
        skills=skills,
        employee_skills=employee_skills,
        impact_scores=scoring_result.scores,
        centrality=net.centrality,
        nexus_ids=net.nexus_ids,
        communities=net.communities,
        team_fragility=net.team_fragility,
        dept_summary=dept_summary,
        team_summary=team_summary,
        quarterly_spend=quarterly_spend,
        quarterly_kpi=quarterly_kpi,
        employee_table=employee_table,
        total_headcount=len(employees),
        total_spend=total_spend,
        total_budget=total_budget,
        avg_impact_score=avg_impact,
        budget_variance_pct=variance_pct,
        n_at_risk_teams=n_at_risk,
        n_nexus_employees=len(net.nexus_ids),
        org_name=org.org_name,
        scenario_id=org.scenario_id,
        org_size=org.org_size,
        graph_density=net.graph_density,
        n_components=net.n_components,
        scoring_mode=scoring_result.mode,
    )


# ---------------------------------------------------------------------------
# Real data loader (DuckDB gold layer)
# ---------------------------------------------------------------------------

def _load_real() -> DashboardData:
    """Load aggregated data from DuckDB gold layer."""
    import os
    import duckdb

    duckdb_path = os.getenv("DUCKDB_PATH", "./data/eibo_analytics.db")
    try:
        duck = duckdb.connect(duckdb_path, read_only=True)
    except Exception as exc:
        raise RuntimeError(
            f"DuckDB at '{duckdb_path}' is not available. "
            "Run the gold aggregation pipeline first, or switch to Demo Mode."
        ) from exc

    try:
        employees = duck.execute("SELECT * FROM gold_impact_inputs").df()
        # Minimal stub — full implementation depends on gold layer tables
        duck.close()
    except Exception as exc:
        duck.close()
        raise RuntimeError(
            f"Gold layer tables not found in DuckDB: {exc}. "
            "Run 'python data_pipeline/gold_aggregate.py' first."
        ) from exc

    # Return a minimal DashboardData from gold layer data
    # Full wiring is left for when real HRIS data is available
    raise NotImplementedError(
        "Real data mode requires running the full ETL pipeline. "
        "Use Demo Mode to explore the platform capabilities."
    )


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _build_dept_summary(
    employees: pd.DataFrame,
    teams: pd.DataFrame,
    scores: pd.DataFrame,
    team_fragility: dict[str, float],
) -> pd.DataFrame:
    """Department-level aggregation: spend, headcount, impact, fragility."""
    team_budget = teams.groupby("department")["annual_budget"].sum().reset_index()
    team_budget.columns = ["department", "annual_budget"]

    emp_enriched = employees.merge(
        scores[["employee_id", "impact_score"]], on="employee_id", how="left"
    )
    emp_enriched["total_cost"] = emp_enriched["annual_salary"] + emp_enriched["annual_benefits"]

    dept_agg = (
        emp_enriched.groupby("department")
        .agg(
            headcount=("employee_id", "count"),
            total_spend=("total_cost", "sum"),
            avg_impact=("impact_score", "mean"),
        )
        .reset_index()
    )

    dept_agg = dept_agg.merge(team_budget, on="department", how="left")
    dept_agg["annual_budget"] = dept_agg["annual_budget"].fillna(0.0)
    dept_agg["budget_variance_pct"] = (
        (dept_agg["total_spend"] - dept_agg["annual_budget"])
        / dept_agg["annual_budget"].replace(0, np.nan)
        * 100
    ).fillna(0.0).round(2)

    dept_agg["avg_impact"] = dept_agg["avg_impact"].round(1).fillna(0.0)

    # Average fragility per department (via team → dept join)
    if team_fragility:
        frag_df = pd.DataFrame(
            list(team_fragility.items()), columns=["team_id", "fragility"]
        )
        dept_frag = (
            employees[["team_id", "department"]]
            .drop_duplicates()
            .merge(frag_df, on="team_id", how="left")
            .groupby("department")["fragility"]
            .mean()
            .reset_index()
        )
        dept_frag.columns = ["department", "fragility_avg"]
        dept_agg = dept_agg.merge(dept_frag, on="department", how="left")
    else:
        dept_agg["fragility_avg"] = 0.0

    return dept_agg.sort_values("total_spend", ascending=False).reset_index(drop=True)


def _build_team_summary(
    employees: pd.DataFrame,
    teams: pd.DataFrame,
    scores: pd.DataFrame,
    team_fragility: dict[str, float],
) -> pd.DataFrame:
    emp_enriched = employees.merge(
        scores[["employee_id", "impact_score"]], on="employee_id", how="left"
    )
    emp_enriched["total_cost"] = emp_enriched["annual_salary"] + emp_enriched["annual_benefits"]

    team_agg = (
        emp_enriched.groupby("team_id")
        .agg(
            headcount=("employee_id", "count"),
            total_spend=("total_cost", "sum"),
            avg_impact=("impact_score", "mean"),
        )
        .reset_index()
    )

    team_agg = team_agg.merge(
        teams[["team_id", "team_name", "department", "annual_budget"]],
        on="team_id",
        how="left",
    )
    team_agg["budget_variance_pct"] = (
        (team_agg["total_spend"] - team_agg["annual_budget"])
        / team_agg["annual_budget"].replace(0, np.nan)
        * 100
    ).fillna(0.0).round(2)

    frag_series = pd.Series(team_fragility).rename("fragility")
    team_agg = team_agg.merge(
        frag_series.reset_index().rename(columns={"index": "team_id"}),
        on="team_id",
        how="left",
    )
    team_agg["fragility"] = team_agg["fragility"].fillna(0.0).round(3)
    team_agg["avg_impact"] = team_agg["avg_impact"].round(1).fillna(0.0)

    return team_agg.sort_values("total_spend", ascending=False).reset_index(drop=True)


def _build_quarterly_spend(budget_df: pd.DataFrame) -> pd.DataFrame:
    if budget_df.empty:
        return pd.DataFrame(
            columns=["fiscal_period", "total_budgeted", "total_actual", "period_start"]
        )

    agg = (
        budget_df.groupby(["fiscal_period", "period_start"])
        .agg(total_budgeted=("budgeted_amount", "sum"),
             total_actual=("actual_amount", "sum"))
        .reset_index()
    )
    agg["period_start"] = pd.to_datetime(agg["period_start"])
    return agg.sort_values("period_start").tail(12).reset_index(drop=True)


def _build_quarterly_kpi(performance_df: pd.DataFrame) -> pd.DataFrame:
    if performance_df.empty:
        return pd.DataFrame(columns=["review_period", "avg_kpi", "n_reviews"])

    agg = (
        performance_df.groupby("review_period")
        .agg(avg_kpi=("kpi_score", "mean"), n_reviews=("kpi_score", "count"))
        .reset_index()
    )
    return agg.sort_values("review_period").tail(12).reset_index(drop=True)


def _build_employee_table(
    employees: pd.DataFrame,
    scores: pd.DataFrame,
    nexus_ids: set[str],
    communities: dict[str, int],
    employee_skills: pd.DataFrame,
    skills: pd.DataFrame,
) -> pd.DataFrame:
    """Denormalized employee table for display."""
    table = employees[
        ["employee_id", "full_name", "role_title", "department",
         "team_id", "seniority_level", "annual_salary", "annual_benefits",
         "hire_date", "location"]
    ].copy()

    table = table.merge(
        scores[["employee_id", "impact_score", "kpi_contribution",
                "network_contribution", "skills_contribution",
                "cost_contribution", "confidence"]],
        on="employee_id",
        how="left",
    )

    table["is_nexus"] = table["employee_id"].isin(nexus_ids)
    table["community_id"] = table["employee_id"].map(communities).fillna(-1).astype(int)

    # Top skill per employee
    if not employee_skills.empty and not skills.empty:
        top_skill = (
            employee_skills[employee_skills["is_primary"] == True]
            .merge(skills[["skill_id", "skill_name"]], on="skill_id", how="left")
            .groupby("employee_id")["skill_name"]
            .first()
            .reset_index()
        )
        top_skill.columns = ["employee_id", "top_skill"]
        table = table.merge(top_skill, on="employee_id", how="left")
    else:
        table["top_skill"] = ""

    table["top_skill"] = table["top_skill"].fillna("")
    table["impact_score"] = table["impact_score"].round(1).fillna(0.0)
    table["total_cost"] = (table["annual_salary"] + table["annual_benefits"]).round(0)

    # Tenure in years
    today = pd.Timestamp.today().normalize()
    table["tenure_years"] = (
        (today - pd.to_datetime(table["hire_date"], errors="coerce")).dt.days / 365.25
    ).clip(lower=0).round(1)

    return table.sort_values("impact_score", ascending=False).reset_index(drop=True)
