"""Early Warning System for workforce risk signals.

Evaluates six risk triggers and returns structured alerts with
severity levels and actionable recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & dataclasses
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MODERATE = "moderate"
    LOW      = "low"
    OK       = "ok"


_SEVERITY_ORDER = {
    Severity.CRITICAL: 4,
    Severity.HIGH: 3,
    Severity.MODERATE: 2,
    Severity.LOW: 1,
    Severity.OK: 0,
}


@dataclass
class Alert:
    """Single early-warning alert."""
    trigger: str                     # machine-readable trigger name
    title: str                       # human-readable title
    severity: Severity
    message: str                     # explanation
    affected_entities: list[str] = field(default_factory=list)   # dept / team / employee IDs
    metric_value: float = 0.0        # quantitative reading
    threshold: float = 0.0           # threshold that was crossed
    recommendation: str = ""

    @property
    def severity_rank(self) -> int:
        return _SEVERITY_ORDER[self.severity]


@dataclass
class EarlyWarningResult:
    """Collection of alerts from all triggers."""
    alerts: list[Alert] = field(default_factory=list)
    overall_severity: Severity = Severity.OK
    generated_at: str = ""

    @property
    def critical_alerts(self) -> list[Alert]:
        return [a for a in self.alerts if a.severity == Severity.CRITICAL]

    @property
    def high_alerts(self) -> list[Alert]:
        return [a for a in self.alerts if a.severity == Severity.HIGH]

    @property
    def ok_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == Severity.OK)

    def by_severity(self) -> list[Alert]:
        return sorted(self.alerts, key=lambda a: -a.severity_rank)


# ---------------------------------------------------------------------------
# Thresholds (configurable — can be overridden by caller)
# ---------------------------------------------------------------------------

@dataclass
class EarlyWarningThresholds:
    attrition_spike_critical: float = 0.35      # fraction of team with High+Critical risk
    attrition_spike_high: float = 0.20
    nexus_attrition_critical: float = 0.65      # attrition_risk for a nexus employee
    nexus_attrition_high: float = 0.45
    fragility_critical: float = 0.75            # team fragility score
    fragility_high: float = 0.55
    budget_overrun_critical: float = 0.95       # fraction of annual budget consumed
    budget_overrun_high: float = 0.85
    impact_decline_threshold: float = -5.0      # points decline in dept avg impact
    skill_gap_critical_team_fraction: float = 0.30  # fraction of teams missing a critical skill


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class EarlyWarningEvaluator:
    """Evaluates workforce data against risk thresholds.

    All methods are independent; each returns zero or more Alert objects.
    """

    def __init__(self, thresholds: Optional[EarlyWarningThresholds] = None) -> None:
        self._t = thresholds or EarlyWarningThresholds()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        employee_df: pd.DataFrame,
        attrition_scores: Optional[pd.DataFrame] = None,
        team_fragility: Optional[dict[str, float]] = None,
        nexus_ids: Optional[set[str]] = None,
        impact_scores: Optional[pd.DataFrame] = None,
        budget_consumed: float = 0.0,
        annual_budget: float = 0.0,
        skill_holders: Optional[dict[str, list[str]]] = None,
        dept_col: str = "department",
        team_col: str = "team_id",
    ) -> EarlyWarningResult:
        """Run all six risk triggers and return aggregated result.

        Args:
            employee_df: Main employee table.
            attrition_scores: DataFrame with employee_id, attrition_risk,
                              risk_category columns.
            team_fragility: {team_id: fragility_score 0-1}.
            nexus_ids: Set of nexus employee IDs.
            impact_scores: DataFrame with employee_id, impact_score, department.
            budget_consumed: Year-to-date actual spend.
            annual_budget: Planned annual budget.
            skill_holders: {skill_name: [employee_ids]} for critical skills.
            dept_col: Department column in employee_df.
            team_col: Team column in employee_df.

        Returns:
            EarlyWarningResult with all triggered alerts.
        """
        alerts: list[Alert] = []

        if attrition_scores is not None and not attrition_scores.empty:
            alerts += self._attrition_spike(
                employee_df, attrition_scores, dept_col, team_col
            )
            if nexus_ids:
                alerts += self._nexus_attrition_risk(attrition_scores, nexus_ids)

        if team_fragility:
            alerts += self._fragility_threshold(team_fragility)

        if annual_budget > 0 and budget_consumed > 0:
            alerts += self._budget_overrun(budget_consumed, annual_budget)

        if impact_scores is not None and not impact_scores.empty:
            alerts += self._impact_decline(impact_scores, dept_col)

        if skill_holders and attrition_scores is not None and not attrition_scores.empty:
            alerts += self._skill_gap_risk(skill_holders, attrition_scores)

        overall = Severity.OK
        if alerts:
            overall = max(alerts, key=lambda a: a.severity_rank).severity

        return EarlyWarningResult(
            alerts=alerts,
            overall_severity=overall,
            generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        )

    # ------------------------------------------------------------------
    # Trigger 1: Attrition spike in critical team
    # ------------------------------------------------------------------

    def _attrition_spike(
        self,
        employee_df: pd.DataFrame,
        attrition_scores: pd.DataFrame,
        dept_col: str,
        team_col: str,
    ) -> list[Alert]:
        alerts: list[Alert] = []
        merged = employee_df.merge(
            attrition_scores[["employee_id", "attrition_risk", "risk_category"]],
            on="employee_id",
            how="left",
        )
        group_col = team_col if team_col in merged.columns else dept_col
        if group_col not in merged.columns:
            return []

        for group_id, grp in merged.groupby(group_col):
            if len(grp) < 3:
                continue
            high_risk = grp["risk_category"].isin(["High", "Critical"]).sum()
            fraction = high_risk / len(grp)

            if fraction >= self._t.attrition_spike_critical:
                sev = Severity.CRITICAL
            elif fraction >= self._t.attrition_spike_high:
                sev = Severity.HIGH
            else:
                continue

            affected = grp.loc[
                grp["risk_category"].isin(["High", "Critical"]), "employee_id"
            ].astype(str).tolist()

            alerts.append(Alert(
                trigger="attrition_spike",
                title=f"Attrition Risk Spike — {group_id}",
                severity=sev,
                message=(
                    f"{high_risk} of {len(grp)} employees in {group_id} "
                    f"({fraction:.0%}) show High or Critical attrition risk."
                ),
                affected_entities=affected,
                metric_value=fraction,
                threshold=self._t.attrition_spike_critical if sev == Severity.CRITICAL
                          else self._t.attrition_spike_high,
                recommendation=(
                    "Schedule retention conversations. Review compensation and "
                    "career development plans for at-risk employees."
                ),
            ))
        return alerts

    # ------------------------------------------------------------------
    # Trigger 2: Nexus employee showing attrition risk
    # ------------------------------------------------------------------

    def _nexus_attrition_risk(
        self,
        attrition_scores: pd.DataFrame,
        nexus_ids: set[str],
    ) -> list[Alert]:
        alerts: list[Alert] = []
        nexus_df = attrition_scores[
            attrition_scores["employee_id"].astype(str).isin(nexus_ids)
        ]
        for _, row in nexus_df.iterrows():
            risk = float(row.get("attrition_risk", 0))
            emp_id = str(row["employee_id"])

            if risk >= self._t.nexus_attrition_critical:
                sev = Severity.CRITICAL
                thresh = self._t.nexus_attrition_critical
            elif risk >= self._t.nexus_attrition_high:
                sev = Severity.HIGH
                thresh = self._t.nexus_attrition_high
            else:
                continue

            alerts.append(Alert(
                trigger="nexus_attrition_risk",
                title=f"Nexus Employee At Risk — {emp_id}",
                severity=sev,
                message=(
                    f"Organizational Nexus employee {emp_id} has attrition risk "
                    f"{risk:.0f}/100. Their departure would fragment the "
                    "collaboration network."
                ),
                affected_entities=[emp_id],
                metric_value=risk,
                threshold=thresh,
                recommendation=(
                    "Initiate proactive retention discussion. Document critical "
                    "knowledge. Identify and develop potential successors."
                ),
            ))
        return alerts

    # ------------------------------------------------------------------
    # Trigger 3: Team fragility exceeding threshold
    # ------------------------------------------------------------------

    def _fragility_threshold(
        self,
        team_fragility: dict[str, float],
    ) -> list[Alert]:
        alerts: list[Alert] = []
        for team_id, score in team_fragility.items():
            if score >= self._t.fragility_critical:
                sev = Severity.CRITICAL
                thresh = self._t.fragility_critical
            elif score >= self._t.fragility_high:
                sev = Severity.HIGH
                thresh = self._t.fragility_high
            else:
                continue

            alerts.append(Alert(
                trigger="team_fragility",
                title=f"High Team Fragility — {team_id}",
                severity=sev,
                message=(
                    f"Team {team_id} fragility score is {score:.0%} — "
                    "critically dependent on a small number of individuals."
                ),
                affected_entities=[str(team_id)],
                metric_value=score,
                threshold=thresh,
                recommendation=(
                    "Cross-train team members. Distribute critical responsibilities. "
                    "Consider knowledge-sharing sessions and documentation sprints."
                ),
            ))
        return alerts

    # ------------------------------------------------------------------
    # Trigger 4: Budget overrun trajectory
    # ------------------------------------------------------------------

    def _budget_overrun(
        self,
        budget_consumed: float,
        annual_budget: float,
    ) -> list[Alert]:
        fraction = budget_consumed / annual_budget
        current_month = pd.Timestamp.today().month
        expected_fraction = current_month / 12

        # Only flag if consumption significantly exceeds expected pace
        pace_ratio = fraction / max(expected_fraction, 0.01)
        if pace_ratio < 1.10:
            return []

        if fraction >= self._t.budget_overrun_critical:
            sev = Severity.CRITICAL
            thresh = self._t.budget_overrun_critical
        elif fraction >= self._t.budget_overrun_high:
            sev = Severity.HIGH
            thresh = self._t.budget_overrun_high
        else:
            sev = Severity.MODERATE
            thresh = expected_fraction

        remaining = annual_budget - budget_consumed
        projected_annual = budget_consumed / max(expected_fraction, 0.01)

        return [Alert(
            trigger="budget_overrun",
            title="Budget Overrun Trajectory",
            severity=sev,
            message=(
                f"Year-to-date spend is {fraction:.0%} of annual budget "
                f"({expected_fraction:.0%} expected at this point in the year). "
                f"Projected annual total: ${projected_annual:,.0f} vs "
                f"budget ${annual_budget:,.0f}."
            ),
            affected_entities=[],
            metric_value=fraction,
            threshold=thresh,
            recommendation=(
                f"Review discretionary spend. Remaining budget: ${remaining:,.0f}. "
                "Run sensitivity analysis to identify optimization opportunities."
            ),
        )]

    # ------------------------------------------------------------------
    # Trigger 5: Department impact score declining trend
    # ------------------------------------------------------------------

    def _impact_decline(
        self,
        impact_scores: pd.DataFrame,
        dept_col: str,
    ) -> list[Alert]:
        alerts: list[Alert] = []
        if dept_col not in impact_scores.columns or "impact_score" not in impact_scores.columns:
            return []

        # Compute dept average; compare to a synthetic "prior" period
        # (without actual historical impact data, we flag depts significantly
        #  below org average as a proxy for declining trend)
        dept_avg = impact_scores.groupby(dept_col)["impact_score"].mean()
        org_avg = dept_avg.mean()
        org_std = dept_avg.std() if len(dept_avg) > 1 else 10.0

        for dept, avg in dept_avg.items():
            delta = avg - org_avg
            if delta < self._t.impact_decline_threshold - org_std:
                sev = Severity.HIGH
            elif delta < self._t.impact_decline_threshold:
                sev = Severity.MODERATE
            else:
                continue

            alerts.append(Alert(
                trigger="impact_decline",
                title=f"Below-Average Impact Concentration — {dept}",
                severity=sev,
                message=(
                    f"Department '{dept}' average impact score ({avg:.1f}) is "
                    f"{abs(delta):.1f} points below the organizational average ({org_avg:.1f})."
                ),
                affected_entities=[str(dept)],
                metric_value=avg,
                threshold=org_avg + self._t.impact_decline_threshold,
                recommendation=(
                    "Investigate performance drivers. Consider targeted development "
                    "programs, skill-building initiatives, or workload redistribution."
                ),
            ))
        return alerts

    # ------------------------------------------------------------------
    # Trigger 6: Critical skill gap risk
    # ------------------------------------------------------------------

    def _skill_gap_risk(
        self,
        skill_holders: dict[str, list[str]],
        attrition_scores: pd.DataFrame,
    ) -> list[Alert]:
        alerts: list[Alert] = []
        risk_lookup = (
            attrition_scores.set_index("employee_id")["attrition_risk"]
            .to_dict()
        ) if "employee_id" in attrition_scores.columns else {}

        for skill, holders in skill_holders.items():
            if not holders:
                alerts.append(Alert(
                    trigger="skill_gap",
                    title=f"Critical Skill Gap — {skill}",
                    severity=Severity.CRITICAL,
                    message=f"No employee currently holds the critical skill '{skill}'.",
                    affected_entities=[],
                    metric_value=0,
                    threshold=1,
                    recommendation=(
                        f"Initiate hiring or upskilling program for '{skill}' immediately."
                    ),
                ))
                continue

            # Average attrition risk among holders
            holder_risks = [float(risk_lookup.get(h, 40)) for h in holders]
            avg_risk = np.mean(holder_risks)
            max_risk = np.max(holder_risks)

            # Single holder is highest risk
            if len(holders) == 1 and avg_risk >= 50:
                sev = Severity.CRITICAL if avg_risk >= 70 else Severity.HIGH
                alerts.append(Alert(
                    trigger="skill_gap",
                    title=f"Single-Point Skill Risk — {skill}",
                    severity=sev,
                    message=(
                        f"'{skill}' is held by only 1 employee with attrition risk "
                        f"{avg_risk:.0f}/100."
                    ),
                    affected_entities=holders,
                    metric_value=avg_risk,
                    threshold=50,
                    recommendation=(
                        f"Prioritise knowledge transfer and cross-training for '{skill}'. "
                        "Consider succession planning."
                    ),
                ))
            elif avg_risk >= 65:
                alerts.append(Alert(
                    trigger="skill_gap",
                    title=f"Skill Retention Risk — {skill}",
                    severity=Severity.HIGH,
                    message=(
                        f"Average attrition risk of '{skill}' holders is {avg_risk:.0f}/100 "
                        f"(highest: {max_risk:.0f})."
                    ),
                    affected_entities=holders,
                    metric_value=avg_risk,
                    threshold=65,
                    recommendation=(
                        f"Expand '{skill}' coverage by upskilling adjacent employees."
                    ),
                ))
        return alerts


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def evaluate_early_warnings(
    employee_df: pd.DataFrame,
    attrition_scores: Optional[pd.DataFrame] = None,
    team_fragility: Optional[dict[str, float]] = None,
    nexus_ids: Optional[set[str]] = None,
    impact_scores: Optional[pd.DataFrame] = None,
    budget_consumed: float = 0.0,
    annual_budget: float = 0.0,
    skill_holders: Optional[dict[str, list[str]]] = None,
    thresholds: Optional[EarlyWarningThresholds] = None,
) -> EarlyWarningResult:
    """Evaluate early warning triggers. Convenience wrapper."""
    return EarlyWarningEvaluator(thresholds).evaluate(
        employee_df=employee_df,
        attrition_scores=attrition_scores,
        team_fragility=team_fragility,
        nexus_ids=nexus_ids,
        impact_scores=impact_scores,
        budget_consumed=budget_consumed,
        annual_budget=annual_budget,
        skill_holders=skill_holders,
    )
