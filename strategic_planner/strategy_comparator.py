"""Strategic Scenario Comparator — compare workforce strategies on multi-criteria scoring.

Evaluates 4+ strategy archetypes or custom strategies on: 2-year cost,
talent retention, innovation capacity, operational resilience, and execution time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strategy definitions
# ---------------------------------------------------------------------------

@dataclass
class WorkforceStrategy:
    """A workforce strategy scenario."""
    name: str
    description: str
    # Budget lever (relative to current annual spend)
    budget_change_pct: float = 0.0       # e.g. -0.10 = 10% reduction
    # Priority weights (0–1, must not all be zero)
    retention_priority: float = 0.5
    growth_priority:    float = 0.3
    optimization_priority: float = 0.2
    # Staffing model
    external_hire_rate: float = 0.05     # % of headcount hired externally per year
    training_investment_pct: float = 0.02  # % of payroll invested in training
    # Custom tag for display
    color: str = "#6B7280"

    def __post_init__(self) -> None:
        total = self.retention_priority + self.growth_priority + self.optimization_priority
        if total > 0:
            self.retention_priority    /= total
            self.growth_priority       /= total
            self.optimization_priority /= total


# ---------------------------------------------------------------------------
# Preset strategy archetypes
# ---------------------------------------------------------------------------

PRESET_STRATEGIES: list[WorkforceStrategy] = [
    WorkforceStrategy(
        name="Aggressive Optimisation",
        description=(
            "Significant cost reduction through consolidation, "
            "automation, and headcount rightsizing. "
            "Prioritises financial efficiency over talent preservation."
        ),
        budget_change_pct=-0.15,
        retention_priority=0.2,
        growth_priority=0.1,
        optimization_priority=0.7,
        external_hire_rate=0.02,
        training_investment_pct=0.01,
        color="#F07020",
    ),
    WorkforceStrategy(
        name="Talent-First Preservation",
        description=(
            "Protect critical talent and institutional knowledge at all costs. "
            "Absorbs near-term cost pressure in exchange for long-term capability."
        ),
        budget_change_pct=0.05,
        retention_priority=0.75,
        growth_priority=0.15,
        optimization_priority=0.10,
        external_hire_rate=0.03,
        training_investment_pct=0.04,
        color="#27B97C",
    ),
    WorkforceStrategy(
        name="Balanced Approach",
        description=(
            "Moderate cost discipline with sustained talent investment. "
            "Targets 5% efficiency gain while protecting high-impact roles."
        ),
        budget_change_pct=-0.05,
        retention_priority=0.40,
        growth_priority=0.30,
        optimization_priority=0.30,
        external_hire_rate=0.04,
        training_investment_pct=0.025,
        color="#7C4DBD",
    ),
    WorkforceStrategy(
        name="Growth Investment",
        description=(
            "Invest ahead of business growth: hire for new capabilities, "
            "build skills pipeline, and expand team capacity. "
            "Near-term cost increase, long-term competitive advantage."
        ),
        budget_change_pct=0.12,
        retention_priority=0.35,
        growth_priority=0.55,
        optimization_priority=0.10,
        external_hire_rate=0.12,
        training_investment_pct=0.05,
        color="#C8982A",
    ),
]


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StrategyScore:
    """Multi-criteria score for a single strategy."""
    strategy_name: str
    color: str

    # Raw metrics
    two_year_cost: float
    retention_rate_projection: float     # 0–1
    innovation_capacity_score: float     # 0–100
    operational_resilience_score: float  # 0–100
    months_to_execute: int

    # Sub-scores (normalised 0–100)
    cost_score: float          # higher = cheaper (inverted)
    retention_score: float
    innovation_score: float
    resilience_score: float
    speed_score: float         # higher = faster

    # Composite
    overall_score: float       # weighted by org_priorities
    rank: int = 0

    # Narrative
    recommendation: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Full multi-strategy comparison output."""
    scores: list[StrategyScore]
    recommended_strategy: str
    recommendation_rationale: str
    radar_df: pd.DataFrame           # wide: strategy_name | cost | retention | ...
    comparison_df: pd.DataFrame      # long format for Plotly
    org_priorities: dict[str, float] # what the org weighted
    generated_at: str = ""

    @property
    def winner(self) -> StrategyScore:
        return min(self.scores, key=lambda s: s.rank)


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------

class StrategyComparator:
    """Compares workforce strategies using weighted multi-criteria scoring.

    Args:
        org_priorities: Dict with keys 'cost', 'retention', 'innovation',
                        'resilience', 'speed'. Values are weights (will be
                        normalised to sum to 1).
    """

    _DEFAULT_PRIORITIES = {
        "cost":       0.30,
        "retention":  0.25,
        "innovation": 0.20,
        "resilience": 0.15,
        "speed":      0.10,
    }

    def __init__(
        self,
        org_priorities: dict[str, float] | None = None,
    ) -> None:
        raw = org_priorities or self._DEFAULT_PRIORITIES
        total = sum(raw.values()) or 1.0
        self._priorities = {k: v / total for k, v in raw.items()}

    def compare(
        self,
        strategies: list[WorkforceStrategy],
        current_annual_spend: float,
        n_employees: int,
        avg_impact_score: float = 60.0,
        n_nexus: int = 0,
        attrition_rate: float = 0.12,
    ) -> ComparisonResult:
        """Run multi-criteria comparison across all strategies.

        Args:
            strategies: List of WorkforceStrategy to compare.
            current_annual_spend: Current annual payroll + benefits.
            n_employees: Current headcount.
            avg_impact_score: Org average impact score 0–100.
            n_nexus: Number of Nexus employees.
            attrition_rate: Current annual voluntary attrition rate 0–1.

        Returns:
            ComparisonResult with ranked strategies and recommendation.
        """
        raw_scores = [
            self._score_strategy(s, current_annual_spend, n_employees,
                                  avg_impact_score, n_nexus, attrition_rate)
            for s in strategies
        ]

        # Normalise sub-scores across strategies for fair comparison
        normalised = self._normalise_scores(raw_scores)

        # Compute weighted composite
        for s in normalised:
            s.overall_score = round(
                self._priorities["cost"]       * s.cost_score +
                self._priorities["retention"]  * s.retention_score +
                self._priorities["innovation"] * s.innovation_score +
                self._priorities["resilience"] * s.resilience_score +
                self._priorities["speed"]      * s.speed_score,
                1,
            )

        # Rank
        sorted_scores = sorted(normalised, key=lambda s: -s.overall_score)
        for i, s in enumerate(sorted_scores):
            s.rank = i + 1

        # Build narratives
        for s in sorted_scores:
            s.recommendation, s.strengths, s.weaknesses = self._build_narrative(s, sorted_scores[0])

        winner = sorted_scores[0]
        rationale = (
            f"**{winner.strategy_name}** scores highest ({winner.overall_score:.0f}/100) "
            f"given your organisational priorities "
            f"(cost weight {self._priorities['cost']:.0%}, "
            f"retention {self._priorities['retention']:.0%}, "
            f"innovation {self._priorities['innovation']:.0%}). "
            f"2-year cost projection: ${winner.two_year_cost:,.0f}."
        )

        radar_df = self._build_radar_df(sorted_scores)
        comparison_df = self._build_comparison_df(sorted_scores)

        return ComparisonResult(
            scores=sorted_scores,
            recommended_strategy=winner.strategy_name,
            recommendation_rationale=rationale,
            radar_df=radar_df,
            comparison_df=comparison_df,
            org_priorities=self._priorities,
            generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        )

    # ------------------------------------------------------------------
    # Per-strategy raw scoring
    # ------------------------------------------------------------------

    def _score_strategy(
        self,
        strategy: WorkforceStrategy,
        current_spend: float,
        n_employees: int,
        avg_impact: float,
        n_nexus: int,
        attrition_rate: float,
    ) -> StrategyScore:
        # 2-year cost
        yr1_spend = current_spend * (1 + strategy.budget_change_pct)
        yr1_training = yr1_spend * strategy.training_investment_pct
        yr1_hiring = current_spend * strategy.external_hire_rate * 1.18  # + fee
        yr1_total = yr1_spend + yr1_training + yr1_hiring

        yr2_spend = yr1_spend * (1 + strategy.budget_change_pct * 0.5)  # diminishing effect
        two_year_cost = yr1_total + yr2_spend

        # Retention projection
        base_attrition = attrition_rate
        retention_modifier = (
            -0.08 * strategy.optimization_priority +  # cuts harm retention
             0.06 * strategy.retention_priority +
             0.04 * strategy.training_investment_pct / 0.03
        )
        projected_attrition = np.clip(base_attrition + retention_modifier, 0.03, 0.35)
        retention_rate = 1 - projected_attrition

        # Innovation capacity (driven by growth + training investment)
        innovation = (
            50 +
            30 * strategy.growth_priority +
            20 * (strategy.training_investment_pct / 0.05) +
            10 * strategy.external_hire_rate / 0.10 +
            avg_impact / 10
        )
        innovation = np.clip(innovation, 0, 100)

        # Operational resilience (driven by retention + nexus risk)
        nexus_pct = n_nexus / max(n_employees, 1)
        resilience = (
            60 +
            25 * strategy.retention_priority +
            15 * (1 - projected_attrition) -
            20 * nexus_pct * strategy.optimization_priority  # cuts can hit nexus
        )
        resilience = np.clip(resilience, 0, 100)

        # Months to execute
        months = int(
            4 +
            abs(strategy.budget_change_pct) * 20 +
            strategy.external_hire_rate * 12 +
            strategy.growth_priority * 6
        )

        return StrategyScore(
            strategy_name=strategy.name,
            color=strategy.color,
            two_year_cost=two_year_cost,
            retention_rate_projection=round(retention_rate, 3),
            innovation_capacity_score=round(innovation, 1),
            operational_resilience_score=round(resilience, 1),
            months_to_execute=months,
            # sub-scores filled during normalisation
            cost_score=0.0,
            retention_score=0.0,
            innovation_score=0.0,
            resilience_score=0.0,
            speed_score=0.0,
            overall_score=0.0,
        )

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def _normalise_scores(self, scores: list[StrategyScore]) -> list[StrategyScore]:
        """Normalise each dimension to 0–100 across all strategies."""
        def _norm(vals: list[float], invert: bool = False) -> list[float]:
            mn, mx = min(vals), max(vals)
            if mx == mn:
                return [50.0] * len(vals)
            normalised = [(v - mn) / (mx - mn) * 100 for v in vals]
            return [100 - n for n in normalised] if invert else normalised

        costs       = [s.two_year_cost for s in scores]
        retentions  = [s.retention_rate_projection for s in scores]
        innovations = [s.innovation_capacity_score for s in scores]
        resiliences = [s.operational_resilience_score for s in scores]
        speeds      = [s.months_to_execute for s in scores]

        cost_scores      = _norm(costs, invert=True)      # lower cost = higher score
        retention_scores = _norm(retentions)
        innovation_scores = _norm(innovations)
        resilience_scores = _norm(resiliences)
        speed_scores     = _norm(speeds, invert=True)     # fewer months = higher score

        for i, s in enumerate(scores):
            s.cost_score       = round(cost_scores[i], 1)
            s.retention_score  = round(retention_scores[i], 1)
            s.innovation_score = round(innovation_scores[i], 1)
            s.resilience_score = round(resilience_scores[i], 1)
            s.speed_score      = round(speed_scores[i], 1)

        return scores

    # ------------------------------------------------------------------
    # Narrative builder
    # ------------------------------------------------------------------

    def _build_narrative(
        self, score: StrategyScore, winner: StrategyScore
    ) -> tuple[str, list[str], list[str]]:
        strengths = []
        weaknesses = []

        dims = [
            ("cost_score",       "Cost efficiency"),
            ("retention_score",  "Talent retention"),
            ("innovation_score", "Innovation capacity"),
            ("resilience_score", "Operational resilience"),
            ("speed_score",      "Execution speed"),
        ]
        for attr, label in dims:
            val = getattr(score, attr)
            if val >= 70:
                strengths.append(f"{label} ({val:.0f}/100)")
            elif val <= 35:
                weaknesses.append(f"{label} ({val:.0f}/100)")

        if score.rank == 1:
            rec = "Recommended — highest weighted score given your priorities."
        elif score.rank == 2:
            rec = "Strong alternative if primary recommendation is not feasible."
        else:
            rec = f"Ranked #{score.rank}. Consider if priorities shift significantly."

        return rec, strengths, weaknesses

    # ------------------------------------------------------------------
    # DataFrame builders
    # ------------------------------------------------------------------

    def _build_radar_df(self, scores: list[StrategyScore]) -> pd.DataFrame:
        rows = []
        for s in scores:
            rows.append({
                "Strategy":   s.strategy_name,
                "Cost":       s.cost_score,
                "Retention":  s.retention_score,
                "Innovation": s.innovation_score,
                "Resilience": s.resilience_score,
                "Speed":      s.speed_score,
                "Overall":    s.overall_score,
                "Color":      s.color,
            })
        return pd.DataFrame(rows)

    def _build_comparison_df(self, scores: list[StrategyScore]) -> pd.DataFrame:
        rows = []
        for s in scores:
            rows.append({
                "Strategy":         s.strategy_name,
                "2-Year Cost ($)":  s.two_year_cost,
                "Retention Rate":   f"{s.retention_rate_projection:.0%}",
                "Innovation":       s.innovation_capacity_score,
                "Resilience":       s.operational_resilience_score,
                "Months to Execute": s.months_to_execute,
                "Overall Score":    s.overall_score,
                "Rank":             s.rank,
                "Color":            s.color,
            })
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def compare_strategies(
    strategies: list[WorkforceStrategy] | None = None,
    current_annual_spend: float = 5_000_000,
    n_employees: int = 100,
    avg_impact_score: float = 60.0,
    n_nexus: int = 5,
    attrition_rate: float = 0.12,
    org_priorities: dict[str, float] | None = None,
) -> ComparisonResult:
    """Run strategy comparison. Convenience wrapper using preset strategies."""
    strats = strategies or PRESET_STRATEGIES
    return StrategyComparator(org_priorities).compare(
        strats, current_annual_spend, n_employees,
        avg_impact_score, n_nexus, attrition_rate
    )
