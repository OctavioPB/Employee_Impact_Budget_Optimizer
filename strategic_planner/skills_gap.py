"""Skills Gap Analysis — current vs required skills, build vs buy recommendations.

Identifies gaps between current workforce skills and future requirements,
computes build-vs-buy cost comparison, and finds adjacency candidates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Input dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SkillRequirement:
    """A skill the organization needs in its future state."""
    skill_name: str
    required_proficiency: int = 3    # 1–5
    required_headcount: int = 1
    horizon_months: int = 12         # 12 or 24
    is_critical: bool = False


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AdjacencyCandidate:
    employee_id: str
    full_name: str
    current_skills: list[str]
    adjacency_score: float            # 0–100: how close current skills are to target
    training_months: float
    training_cost: float


@dataclass
class SkillGapResult:
    """Analysis for a single required skill."""
    skill_name: str
    required_headcount: int
    current_holders: int
    gap: int                          # negative = shortage, positive = surplus
    coverage_pct: float               # current_holders / required * 100
    severity: str                     # "Critical" | "High" | "Moderate" | "Low" | "Covered"
    is_critical: bool

    # Build path
    build_cost_total: float
    build_time_months: float

    # Buy path
    buy_cost_total: float             # salary + hiring fee per head × gap
    buy_time_months: float

    # Recommendation
    recommendation: str               # "Build" | "Buy" | "Hybrid" | "Covered"
    recommendation_rationale: str

    # Default field last to satisfy dataclass ordering rules
    adjacency_candidates: list[AdjacencyCandidate] = field(default_factory=list)


@dataclass
class SkillsGapAnalysis:
    """Full output of SkillsGapAnalyzer."""
    gaps: list[SkillGapResult]
    total_build_cost: float
    total_buy_cost: float
    total_hybrid_cost: float          # recommended path total
    n_critical_gaps: int
    n_covered: int
    generated_at: str = ""

    @property
    def gap_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "skill": g.skill_name,
            "required": g.required_headcount,
            "current": g.current_holders,
            "gap": g.gap,
            "coverage": g.coverage_pct,
            "severity": g.severity,
            "critical": g.is_critical,
            "build_cost": g.build_cost_total,
            "buy_cost": g.buy_cost_total,
            "recommendation": g.recommendation,
            "build_months": g.build_time_months,
            "buy_months": g.buy_time_months,
        } for g in self.gaps])


# ---------------------------------------------------------------------------
# Cost constants
# ---------------------------------------------------------------------------

_TRAINING_COST_PER_MONTH  = 1_500    # per employee per month (courses + time)
_SKILL_TRAINING_MONTHS: dict[str, float] = {
    # complexity-based rough estimates
    "default": 3.0,
    "machine_learning": 6.0,
    "kubernetes": 4.0,
    "terraform": 3.0,
    "apache_kafka": 4.0,
    "sql": 1.5,
    "python": 2.0,
    "tableau": 1.5,
    "product_management": 4.0,
    "agile": 1.0,
    "aws": 3.0,
}

_ANNUAL_SALARY_MID   = 110_000
_BENEFITS_MULTIPLIER = 1.25
_HIRING_FEE_RATE     = 0.18
_TIME_TO_HIRE_MONTHS = 2.5

# Adjacency skill graph: skills that are "close" to each other
# Key = target skill; Values = skills that give partial adjacency credit
_ADJACENCY_MAP: dict[str, list[str]] = {
    "machine_learning":  ["python", "statistics", "data_science"],
    "kubernetes":        ["docker", "linux", "devops"],
    "terraform":         ["aws", "cloud", "devops"],
    "apache_kafka":      ["java", "distributed_systems", "python"],
    "sql":               ["data_analysis", "excel", "nosql"],
    "python":            ["java", "r", "golang", "data_science"],
    "aws":               ["gcp", "azure", "cloud", "terraform"],
    "tableau":           ["data_analysis", "excel", "powerbi"],
    "product_management": ["project_management", "agile", "business_analysis"],
    "agile":             ["project_management", "scrum", "product_management"],
}


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class SkillsGapAnalyzer:
    """Analyzes workforce skill gaps against future requirements."""

    def analyze(
        self,
        requirements: list[SkillRequirement],
        employees_df: pd.DataFrame,
        employee_skills_df: pd.DataFrame,
        skills_df: pd.DataFrame,
    ) -> SkillsGapAnalysis:
        """Run skills gap analysis.

        Args:
            requirements: List of future skill requirements.
            employees_df: Current employees with employee_id, full_name.
            employee_skills_df: employee_id, skill_id, proficiency, is_primary.
            skills_df: skill_id, skill_name.

        Returns:
            SkillsGapAnalysis with per-skill gap results and totals.
        """
        # Build skill lookup
        skill_name_map, _skill_id_map = self._build_skill_maps(skills_df)
        emp_skills = self._build_emp_skill_map(employee_skills_df, skill_name_map)

        gaps: list[SkillGapResult] = []
        for req in requirements:
            gap_result = self._analyze_skill(
                req, employees_df, emp_skills
            )
            gaps.append(gap_result)

        total_build = sum(g.build_cost_total for g in gaps if g.gap < 0)
        total_buy   = sum(g.buy_cost_total   for g in gaps if g.gap < 0)
        total_hybrid = sum(
            min(g.build_cost_total, g.buy_cost_total) if g.gap < 0 else 0
            for g in gaps
        )

        return SkillsGapAnalysis(
            gaps=gaps,
            total_build_cost=total_build,
            total_buy_cost=total_buy,
            total_hybrid_cost=total_hybrid,
            n_critical_gaps=sum(1 for g in gaps if g.severity == "Critical"),
            n_covered=sum(1 for g in gaps if g.severity == "Covered"),
            generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        )

    # ------------------------------------------------------------------
    # Per-skill analysis
    # ------------------------------------------------------------------

    def _analyze_skill(
        self,
        req: SkillRequirement,
        employees_df: pd.DataFrame,
        emp_skills: dict[str, set[str]],
    ) -> SkillGapResult:
        skill_lower = req.skill_name.lower()

        # Count current holders
        holders = [
            eid for eid, skills in emp_skills.items()
            if skill_lower in skills
        ]
        n_holders = len(holders)
        gap = n_holders - req.required_headcount
        coverage = n_holders / max(req.required_headcount, 1) * 100

        severity = self._severity(gap, req.is_critical)

        # Build path
        adjacency = self._find_adjacency_candidates(
            req, employees_df, emp_skills, holders
        )
        training_months = _SKILL_TRAINING_MONTHS.get(skill_lower, _SKILL_TRAINING_MONTHS["default"])
        n_to_train = max(-gap, 0)
        build_cost = n_to_train * training_months * _TRAINING_COST_PER_MONTH
        build_time = training_months if n_to_train > 0 else 0.0

        # Buy path
        annual_cost = _ANNUAL_SALARY_MID * _BENEFITS_MULTIPLIER
        hiring_fee = annual_cost * _HIRING_FEE_RATE
        buy_cost = n_to_train * (annual_cost + hiring_fee) if n_to_train > 0 else 0.0
        buy_time = _TIME_TO_HIRE_MONTHS if n_to_train > 0 else 0.0

        # Recommendation
        rec, rationale = self._recommend(
            gap, build_cost, buy_cost, build_time, buy_time,
            adjacency, req.is_critical, req.horizon_months
        )

        return SkillGapResult(
            skill_name=req.skill_name,
            required_headcount=req.required_headcount,
            current_holders=n_holders,
            gap=gap,
            coverage_pct=round(coverage, 1),
            severity=severity,
            is_critical=req.is_critical,
            build_cost_total=build_cost,
            build_time_months=build_time,
            adjacency_candidates=adjacency,
            buy_cost_total=buy_cost,
            buy_time_months=buy_time,
            recommendation=rec,
            recommendation_rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _severity(self, gap: int, is_critical: bool) -> str:
        if gap >= 0:
            return "Covered"
        shortage = abs(gap)
        if is_critical:
            return "Critical" if shortage >= 1 else "Covered"
        if shortage >= 3:
            return "Critical"
        if shortage == 2:
            return "High"
        return "Moderate"

    def _find_adjacency_candidates(
        self,
        req: SkillRequirement,
        employees_df: pd.DataFrame,
        emp_skills: dict[str, set[str]],
        current_holders: list[str],
    ) -> list[AdjacencyCandidate]:
        """Find employees not holding the target skill but with adjacent skills."""
        if employees_df.empty:
            return []

        skill_lower = req.skill_name.lower()
        adjacent = {s.lower() for s in _ADJACENCY_MAP.get(skill_lower, [])}
        if not adjacent:
            return []

        name_map = {
            str(r["employee_id"]): str(r.get("full_name", r["employee_id"]))
            for _, r in employees_df.iterrows()
        }

        candidates = []
        for eid, skills in emp_skills.items():
            if eid in current_holders:
                continue
            overlap = skills & adjacent
            if not overlap:
                continue
            score = len(overlap) / len(adjacent) * 100
            training_months = _SKILL_TRAINING_MONTHS.get(skill_lower, 3.0) * (
                1 - 0.3 * len(overlap) / len(adjacent)   # adjacency reduces training time
            )
            candidates.append(AdjacencyCandidate(
                employee_id=eid,
                full_name=name_map.get(eid, eid),
                current_skills=list(skills & adjacent),
                adjacency_score=round(score, 1),
                training_months=round(training_months, 1),
                training_cost=training_months * _TRAINING_COST_PER_MONTH,
            ))

        return sorted(candidates, key=lambda c: -c.adjacency_score)[:5]

    def _recommend(
        self,
        gap: int,
        build_cost: float,
        buy_cost: float,
        build_time: float,
        buy_time: float,
        adjacency: list[AdjacencyCandidate],
        is_critical: bool,
        horizon_months: int,
    ) -> tuple[str, str]:
        if gap >= 0:
            return "Covered", "No gap — current workforce meets requirement."

        # Urgency check: if needed within 6 months and build takes > 4 → Buy
        if horizon_months <= 6 and build_time > 4:
            return "Buy", (
                f"Timeline constraint: skill needed within {horizon_months} months "
                f"but upskilling takes {build_time:.0f} months. External hiring recommended."
            )

        # Adjacency check: if strong candidates exist, Build is preferred
        if adjacency and adjacency[0].adjacency_score >= 60 and build_cost < buy_cost * 1.2:
            return "Build", (
                f"{len(adjacency)} employee(s) have strong adjacent skills "
                f"(top score {adjacency[0].adjacency_score:.0f}). "
                f"Upskilling is ${build_cost:,.0f} vs ${buy_cost:,.0f} to hire."
            )

        # Cost comparison with 30% build premium (risk/uncertainty)
        if build_cost * 1.3 < buy_cost:
            return "Build", (
                f"Upskilling is significantly cheaper: ${build_cost:,.0f} vs "
                f"${buy_cost:,.0f} to hire. {build_time:.0f}-month training timeline."
            )

        if buy_cost < build_cost:
            return "Buy", (
                f"External hiring is cost-effective: ${buy_cost:,.0f} vs "
                f"${build_cost:,.0f} to upskill. Immediate skill availability "
                f"(~{buy_time:.0f} months to hire)."
            )

        return "Hybrid", (
            f"Similar cost (build: ${build_cost:,.0f}, hire: ${buy_cost:,.0f}). "
            f"Hybrid: upskill {len(adjacency)} adjacency candidates and hire "
            f"for remaining headcount."
        )

    def _build_skill_maps(
        self,
        skills_df: pd.DataFrame,
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Returns skill_id→name and name→skill_id maps."""
        if skills_df.empty or "skill_id" not in skills_df.columns:
            return {}, {}
        name_map = dict(zip(
            skills_df["skill_id"].astype(str),
            skills_df["skill_name"].str.lower() if "skill_name" in skills_df.columns else skills_df["skill_id"], strict=False,
        ))
        id_map = {v: k for k, v in name_map.items()}
        return name_map, id_map

    def _build_emp_skill_map(
        self,
        employee_skills_df: pd.DataFrame,
        skill_name_map: dict[str, str],
    ) -> dict[str, set[str]]:
        if employee_skills_df.empty:
            return {}
        result: dict[str, set[str]] = {}
        for _, row in employee_skills_df.iterrows():
            eid = str(row["employee_id"])
            sid = str(row.get("skill_id", ""))
            name = skill_name_map.get(sid, sid.lower())
            result.setdefault(eid, set()).add(name)
        return result


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def analyze_skills_gap(
    requirements: list[SkillRequirement],
    employees_df: pd.DataFrame,
    employee_skills_df: pd.DataFrame,
    skills_df: pd.DataFrame,
) -> SkillsGapAnalysis:
    """Run skills gap analysis. Convenience wrapper."""
    return SkillsGapAnalyzer().analyze(requirements, employees_df, employee_skills_df, skills_df)


def build_demo_requirements(employees_df: pd.DataFrame, skills_df: pd.DataFrame) -> list[SkillRequirement]:
    """Synthesize demo requirements scaled to the org size."""
    n = max(len(employees_df), 1)
    scale = max(n // 20, 1)

    base_requirements = [
        SkillRequirement("python",          3, scale * 4, 12, is_critical=True),
        SkillRequirement("machine_learning", 4, scale * 2, 12, is_critical=True),
        SkillRequirement("kubernetes",       3, scale * 2, 12, is_critical=False),
        SkillRequirement("sql",              2, scale * 3, 12, is_critical=False),
        SkillRequirement("apache_kafka",     3, scale * 1, 24, is_critical=True),
        SkillRequirement("product_management", 2, scale * 2, 12, is_critical=False),
        SkillRequirement("agile",            2, scale * 3, 12, is_critical=False),
        SkillRequirement("aws",              3, scale * 2, 12, is_critical=False),
        SkillRequirement("terraform",        3, scale * 1, 24, is_critical=False),
        SkillRequirement("tableau",          2, scale * 2, 12, is_critical=False),
    ]

    # Cross-reference with actual skills in the org
    if not skills_df.empty and "skill_name" in skills_df.columns:
        actual_names = {s.lower() for s in skills_df["skill_name"]}
        return [r for r in base_requirements if r.skill_name.lower() in actual_names or True]

    return base_requirements
