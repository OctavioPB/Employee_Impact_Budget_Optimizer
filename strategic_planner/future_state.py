"""Future State Designer — org structure modeling and transition cost analysis.

Models proposed team structures, matches internal candidates to new roles,
estimates external hiring needs, and projects transition costs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Input dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ProposedRole:
    """A single role definition in a future-state team."""
    role_title: str
    seniority_level: str          # "junior" | "mid" | "senior" | "lead"
    required_skills: list[str] = field(default_factory=list)
    count: int = 1                # headcount for this role
    estimated_salary: float = 0.0  # 0 → auto-estimated from market data

    def __post_init__(self) -> None:
        self.seniority_level = self.seniority_level.lower()


@dataclass
class FutureStateDesign:
    """A proposed future organizational structure."""
    name: str
    description: str
    proposed_teams: dict[str, list[ProposedRole]]  # team_name → roles
    annual_budget_envelope: float = 0.0            # 0 → unconstrained
    horizon_months: int = 12

    @property
    def total_proposed_headcount(self) -> int:
        return sum(r.count for roles in self.proposed_teams.values() for r in roles)

    @property
    def unique_role_count(self) -> int:
        return sum(len(roles) for roles in self.proposed_teams.values())


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class InternalCandidate:
    employee_id: str
    full_name: str
    current_role: str
    proposed_role: str
    match_score: float           # 0–100
    skill_gap: list[str]         # skills the employee is missing
    training_cost: float


@dataclass
class ExternalHiringNeed:
    team_name: str
    role_title: str
    seniority_level: str
    count: int
    estimated_annual_cost: float  # salary + benefits per head
    time_to_hire_months: float


@dataclass
class FutureStateAnalysis:
    """Full analysis of a FutureStateDesign against current workforce."""
    design: FutureStateDesign
    estimated_annual_cost: float
    delta_vs_current: float             # +/- vs current total_spend
    internal_fills: list[InternalCandidate]
    external_hiring_needs: list[ExternalHiringNeed]
    total_transition_cost: float        # severance + hiring fees + training
    severance_cost: float
    hiring_cost: float
    training_cost: float
    months_to_target: int
    budget_feasible: bool               # design cost ≤ envelope (if set)
    warnings: list[str] = field(default_factory=list)

    @property
    def n_internal_fills(self) -> int:
        return len(self.internal_fills)

    @property
    def n_external_hires(self) -> int:
        return sum(n.count for n in self.external_hiring_needs)

    @property
    def internal_fill_rate(self) -> float:
        total_roles = self.design.total_proposed_headcount
        return self.n_internal_fills / max(total_roles, 1)

    def summary_df(self) -> pd.DataFrame:
        rows = []
        for team, roles in self.design.proposed_teams.items():
            for role in roles:
                rows.append({
                    "team": team,
                    "role": role.role_title,
                    "seniority": role.seniority_level,
                    "count": role.count,
                    "est_salary": role.estimated_salary,
                    "team_cost": role.estimated_salary * role.count,
                })
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Salary benchmarks by seniority (USD, annual, fully loaded)
# ---------------------------------------------------------------------------

_SALARY_BENCHMARKS: dict[str, float] = {
    "junior":    75_000,
    "mid":      110_000,
    "senior":   155_000,
    "lead":     185_000,
    "principal": 210_000,
    "director":  220_000,
    "vp":        260_000,
}

_BENEFITS_MULTIPLIER = 1.25   # benefits are 25% on top of salary
_HIRING_FEE_RATE    = 0.18    # recruiter fee = 18% of first-year salary
_SEVERANCE_MONTHS   = 2.0     # months of salary paid as severance
_TIME_TO_HIRE: dict[str, float] = {
    "junior": 1.5, "mid": 2.0, "senior": 3.0, "lead": 4.0,
}


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class FutureStateAnalyzer:
    """Analyzes a FutureStateDesign against the current workforce.

    Args:
        training_cost_per_skill: Estimated cost to train one skill gap per employee.
    """

    def __init__(self, training_cost_per_skill: float = 3_500) -> None:
        self._training_cost_per_skill = training_cost_per_skill

    def analyze(
        self,
        design: FutureStateDesign,
        employees_df: pd.DataFrame,
        employee_skills_df: pd.DataFrame,
        skills_df: pd.DataFrame,
        current_total_spend: float = 0.0,
    ) -> FutureStateAnalysis:
        """Run full future-state analysis.

        Args:
            design: The proposed org structure to evaluate.
            employees_df: Current employee snapshot.
            employee_skills_df: employee_id, skill_id, proficiency, is_primary.
            skills_df: skill_id, skill_name, category, is_critical.
            current_total_spend: Annual total compensation spend (for delta).

        Returns:
            FutureStateAnalysis with full cost, staffing, and transition analysis.
        """
        warnings: list[str] = []

        # Resolve salary estimates
        self._fill_salary_estimates(design)

        # Estimated annual cost of proposed structure
        estimated_cost = self._estimate_annual_cost(design)

        # Build skill name → skill_id lookup
        skill_lookup = self._build_skill_lookup(skills_df)
        # Build employee → set of skill names
        emp_skills = self._build_emp_skills(employees_df, employee_skills_df, skills_df)

        # Find best internal candidates per role
        internal_fills = self._match_internal_candidates(design, employees_df, emp_skills, skill_lookup)

        # Identify unmet roles needing external hiring
        external_needs = self._compute_external_needs(design, internal_fills)

        # Compute transition costs
        severance = self._compute_severance(employees_df, design, current_total_spend)
        hiring_cost = sum(
            n.count * n.estimated_annual_cost * _HIRING_FEE_RATE
            for n in external_needs
        )
        training_cost = sum(
            len(c.skill_gap) * self._training_cost_per_skill
            for c in internal_fills
        )
        total_transition = severance + hiring_cost + training_cost

        # Timeline estimate
        max_hire_months = max(
            (_TIME_TO_HIRE.get(n.seniority_level, 2.5) for n in external_needs),
            default=0,
        )
        months_to_target = int(np.ceil(max_hire_months + 1.0))

        if design.annual_budget_envelope > 0 and estimated_cost > design.annual_budget_envelope:
            warnings.append(
                f"Proposed structure cost (${estimated_cost:,.0f}) exceeds "
                f"budget envelope (${design.annual_budget_envelope:,.0f}) by "
                f"${estimated_cost - design.annual_budget_envelope:,.0f}."
            )

        return FutureStateAnalysis(
            design=design,
            estimated_annual_cost=estimated_cost,
            delta_vs_current=estimated_cost - current_total_spend,
            internal_fills=internal_fills,
            external_hiring_needs=external_needs,
            total_transition_cost=total_transition,
            severance_cost=severance,
            hiring_cost=hiring_cost,
            training_cost=training_cost,
            months_to_target=months_to_target,
            budget_feasible=(
                design.annual_budget_envelope <= 0
                or estimated_cost <= design.annual_budget_envelope
            ),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fill_salary_estimates(self, design: FutureStateDesign) -> None:
        for roles in design.proposed_teams.values():
            for role in roles:
                if role.estimated_salary == 0:
                    role.estimated_salary = (
                        _SALARY_BENCHMARKS.get(role.seniority_level, 110_000)
                        * _BENEFITS_MULTIPLIER
                    )

    def _estimate_annual_cost(self, design: FutureStateDesign) -> float:
        return sum(
            role.estimated_salary * role.count
            for roles in design.proposed_teams.values()
            for role in roles
        )

    def _build_skill_lookup(self, skills_df: pd.DataFrame) -> dict[str, str]:
        """skill_name (lower) → skill_id."""
        if skills_df.empty or "skill_name" not in skills_df.columns:
            return {}
        return {
            str(row["skill_name"]).lower(): str(row["skill_id"])
            for _, row in skills_df.iterrows()
        }

    def _build_emp_skills(
        self,
        employees_df: pd.DataFrame,
        employee_skills_df: pd.DataFrame,
        skills_df: pd.DataFrame,
    ) -> dict[str, set[str]]:
        """employee_id → set of skill_names (lowercase) they hold."""
        if employee_skills_df.empty or skills_df.empty:
            return {str(eid): set() for eid in employees_df.get("employee_id", [])}

        skill_name_map = {}
        if "skill_id" in skills_df.columns and "skill_name" in skills_df.columns:
            skill_name_map = dict(zip(skills_df["skill_id"].astype(str),
                                      skills_df["skill_name"].str.lower()))

        result: dict[str, set[str]] = {}
        for _, row in employee_skills_df.iterrows():
            eid = str(row["employee_id"])
            sid = str(row.get("skill_id", ""))
            skill_name = skill_name_map.get(sid, sid.lower())
            result.setdefault(eid, set()).add(skill_name)

        return result

    def _match_internal_candidates(
        self,
        design: FutureStateDesign,
        employees_df: pd.DataFrame,
        emp_skills: dict[str, set[str]],
        skill_lookup: dict[str, str],
    ) -> list[InternalCandidate]:
        """For each proposed role, find the best-matched current employee."""
        emp_list = employees_df.to_dict("records") if not employees_df.empty else []
        name_map = {
            str(e["employee_id"]): str(e.get("full_name", e["employee_id"]))
            for e in emp_list
        }
        role_map = {
            str(e["employee_id"]): str(e.get("role_title", ""))
            for e in emp_list
        }
        seniority_map = {
            str(e["employee_id"]): str(e.get("seniority_level", "mid")).lower()
            for e in emp_list
        }
        salary_map = {
            str(e["employee_id"]): float(e.get("annual_salary", 0))
            for e in emp_list
        }

        assigned: set[str] = set()
        candidates: list[InternalCandidate] = []

        for team_name, roles in design.proposed_teams.items():
            for role in roles:
                required = {s.lower() for s in role.required_skills}
                for _ in range(role.count):
                    best_emp = None
                    best_score = -1.0

                    for emp in emp_list:
                        eid = str(emp["employee_id"])
                        if eid in assigned:
                            continue
                        seniority_match = (
                            seniority_map.get(eid, "mid") == role.seniority_level
                        )
                        emp_skill_set = emp_skills.get(eid, set())
                        skill_match = (
                            len(required & emp_skill_set) / max(len(required), 1)
                            if required else 1.0
                        )
                        score = (
                            0.5 * float(seniority_match) +
                            0.5 * skill_match
                        ) * 100

                        if score > best_score:
                            best_score = score
                            best_emp = eid

                    # Only accept if score ≥ 40 (at least minimal fit)
                    if best_emp and best_score >= 40:
                        emp_skill_set = emp_skills.get(best_emp, set())
                        gap = list(required - emp_skill_set)
                        training = len(gap) * self._training_cost_per_skill
                        candidates.append(InternalCandidate(
                            employee_id=best_emp,
                            full_name=name_map.get(best_emp, best_emp),
                            current_role=role_map.get(best_emp, ""),
                            proposed_role=role.role_title,
                            match_score=round(best_score, 1),
                            skill_gap=gap,
                            training_cost=training,
                        ))
                        assigned.add(best_emp)

        return candidates

    def _compute_external_needs(
        self,
        design: FutureStateDesign,
        internal_fills: list[InternalCandidate],
    ) -> list[ExternalHiringNeed]:
        """Roles not covered by internal candidates require external hiring."""
        # Count how many internal fills exist per (team, role)
        fill_counts: dict[str, int] = {}
        for c in internal_fills:
            fill_counts[c.proposed_role] = fill_counts.get(c.proposed_role, 0) + 1

        needs = []
        for team_name, roles in design.proposed_teams.items():
            for role in roles:
                filled = fill_counts.get(role.role_title, 0)
                remaining = role.count - filled
                if remaining > 0:
                    needs.append(ExternalHiringNeed(
                        team_name=team_name,
                        role_title=role.role_title,
                        seniority_level=role.seniority_level,
                        count=remaining,
                        estimated_annual_cost=role.estimated_salary,
                        time_to_hire_months=_TIME_TO_HIRE.get(role.seniority_level, 2.5),
                    ))
        return needs

    def _compute_severance(
        self,
        employees_df: pd.DataFrame,
        design: FutureStateDesign,
        current_total_spend: float,
    ) -> float:
        """Estimate severance for headcount reduction."""
        current_hc = len(employees_df) if not employees_df.empty else 0
        proposed_hc = design.total_proposed_headcount
        reduction = max(current_hc - proposed_hc, 0)
        if reduction == 0:
            return 0.0
        avg_monthly = (current_total_spend / 12) / max(current_hc, 1)
        return reduction * avg_monthly * _SEVERANCE_MONTHS


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def analyze_future_state(
    design: FutureStateDesign,
    employees_df: pd.DataFrame,
    employee_skills_df: pd.DataFrame,
    skills_df: pd.DataFrame,
    current_total_spend: float = 0.0,
) -> FutureStateAnalysis:
    """Analyze a future state design. Convenience wrapper."""
    return FutureStateAnalyzer().analyze(
        design, employees_df, employee_skills_df, skills_df, current_total_spend
    )


def build_demo_design(
    org_size: str = "medium",
    scenario: str = "A",
) -> FutureStateDesign:
    """Return a demo FutureStateDesign for the UI."""
    size_budgets = {"small": 2_500_000, "medium": 18_000_000, "large": 180_000_000}
    budget = size_budgets.get(org_size, 18_000_000)

    return FutureStateDesign(
        name="2026 Target Structure",
        description=(
            "Consolidate delivery teams, strengthen platform engineering, "
            "and invest in data & AI capabilities."
        ),
        annual_budget_envelope=budget * 0.95,  # 5% reduction target
        horizon_months=12,
        proposed_teams={
            "Platform Engineering": [
                ProposedRole("Staff Engineer", "senior", ["python", "kubernetes", "aws"], count=3),
                ProposedRole("Platform Engineer", "mid", ["python", "terraform"], count=5),
                ProposedRole("Junior Engineer", "junior", ["python"], count=2),
            ],
            "Data & AI": [
                ProposedRole("ML Engineer", "senior", ["python", "machine_learning"], count=2),
                ProposedRole("Data Engineer", "mid", ["python", "sql", "apache_kafka"], count=3),
                ProposedRole("Data Analyst", "mid", ["sql", "tableau"], count=2),
            ],
            "Product": [
                ProposedRole("Senior PM", "senior", ["product_management"], count=2),
                ProposedRole("PM", "mid", ["product_management", "agile"], count=3),
            ],
            "Operations": [
                ProposedRole("Operations Lead", "lead", ["project_management"], count=1),
                ProposedRole("Operations Analyst", "mid", ["excel", "sql"], count=3),
            ],
        },
    )
