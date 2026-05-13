"""Workforce Transition Planner — phased roadmap from current to future state.

Generates a 3-phase transition plan (0–3 months, 3–9 months, 9–24 months)
with action lists, cost estimates, and risk assessments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from strategic_planner.future_state import FutureStateAnalysis
from strategic_planner.skills_gap import SkillsGapAnalysis

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TransitionAction:
    """A single action within a transition phase."""
    action_type: str       # "hire" | "train" | "restructure" | "communicate" | "document"
    description: str
    owner: str             # "HR" | "Engineering" | "Leadership" | "Finance"
    cost_estimate: float
    duration_weeks: int
    priority: str          # "Critical" | "High" | "Medium" | "Low"
    dependencies: list[str] = field(default_factory=list)


@dataclass
class TransitionPhase:
    """One phase of the workforce transition roadmap."""
    name: str
    months_start: int
    months_end: int
    theme: str
    actions: list[TransitionAction] = field(default_factory=list)
    headcount_change: int = 0
    cost_estimate: float = 0.0
    risk_level: str = "Low"

    @property
    def duration_months(self) -> int:
        return self.months_end - self.months_start

    @property
    def n_actions(self) -> int:
        return len(self.actions)

    def by_type(self, action_type: str) -> list[TransitionAction]:
        return [a for a in self.actions if a.action_type == action_type]


@dataclass
class TransitionRisk:
    """A specific risk in the transition plan."""
    category: str          # "knowledge_loss" | "productivity" | "retention" | "cultural"
    description: str
    probability: str       # "High" | "Medium" | "Low"
    impact: str            # "High" | "Medium" | "Low"
    mitigation: str


@dataclass
class TransitionPlan:
    """Full phased transition plan."""
    phases: list[TransitionPhase]
    risks: list[TransitionRisk]
    total_transition_cost: float
    total_months: int
    knowledge_loss_risk: str      # "High" | "Medium" | "Low"
    productivity_dip_pct: float   # estimated % dip during peak disruption
    recommended_start_month: int  # 0 = immediately, N = defer N months
    executive_summary: str
    generated_at: str = ""

    @property
    def gantt_df(self) -> pd.DataFrame:
        """DataFrame suitable for a simple Gantt chart."""
        rows = []
        for phase in self.phases:
            rows.append({
                "phase": phase.name,
                "start": phase.months_start,
                "end": phase.months_end,
                "cost": phase.cost_estimate,
                "risk": phase.risk_level,
                "n_actions": phase.n_actions,
            })
        return pd.DataFrame(rows)

    @property
    def action_df(self) -> pd.DataFrame:
        rows = []
        for phase in self.phases:
            for action in phase.actions:
                rows.append({
                    "phase": phase.name,
                    "type": action.action_type,
                    "description": action.description,
                    "owner": action.owner,
                    "cost": action.cost_estimate,
                    "duration_weeks": action.duration_weeks,
                    "priority": action.priority,
                })
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class TransitionPlanner:
    """Generates a phased workforce transition roadmap.

    Takes a FutureStateAnalysis and SkillsGapAnalysis as inputs and produces
    a 3-phase plan spanning the transition horizon.
    """

    def plan(
        self,
        future_analysis: FutureStateAnalysis,
        skills_analysis: Optional[SkillsGapAnalysis],
        current_employees_df: pd.DataFrame,
        nexus_ids: Optional[set[str]] = None,
    ) -> TransitionPlan:
        """Generate the transition plan.

        Args:
            future_analysis: Output of FutureStateAnalyzer.analyze().
            skills_analysis: Output of SkillsGapAnalyzer.analyze() (optional).
            current_employees_df: Current employee snapshot.
            nexus_ids: Set of nexus employee IDs (flagged for knowledge doc priority).

        Returns:
            TransitionPlan with 3 phases, risks, and executive summary.
        """
        nexus_ids = nexus_ids or set()
        n_current = len(current_employees_df) if not current_employees_df.empty else 0
        n_proposed = future_analysis.design.total_proposed_headcount
        n_hires = future_analysis.n_external_hires
        n_trains = len(future_analysis.internal_fills)
        n_exits = max(n_current - n_proposed + n_hires - n_trains, 0)

        phase1 = self._phase1_foundation(future_analysis, skills_analysis, nexus_ids, n_exits)
        phase2 = self._phase2_execution(future_analysis, skills_analysis, n_hires, n_trains)
        phase3 = self._phase3_stabilisation(future_analysis, skills_analysis)

        risks = self._assess_risks(
            future_analysis, skills_analysis, nexus_ids, n_exits, n_hires
        )

        knowledge_risk = self._knowledge_loss_risk(nexus_ids, n_exits, n_current)
        productivity_dip = self._productivity_dip(n_exits, n_hires, n_current)
        total_cost = sum(p.cost_estimate for p in [phase1, phase2, phase3])
        total_months = phase3.months_end

        summary = self._executive_summary(
            future_analysis, n_hires, n_exits, n_trains, total_cost,
            knowledge_risk, productivity_dip
        )

        return TransitionPlan(
            phases=[phase1, phase2, phase3],
            risks=risks,
            total_transition_cost=total_cost,
            total_months=total_months,
            knowledge_loss_risk=knowledge_risk,
            productivity_dip_pct=productivity_dip,
            recommended_start_month=0,
            executive_summary=summary,
            generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        )

    # ------------------------------------------------------------------
    # Phase builders
    # ------------------------------------------------------------------

    def _phase1_foundation(
        self,
        fa: FutureStateAnalysis,
        sa: Optional[SkillsGapAnalysis],
        nexus_ids: set[str],
        n_exits: int,
    ) -> TransitionPhase:
        """Phase 1 (months 0–3): Foundation — communicate, document, plan."""
        actions: list[TransitionAction] = []

        # Communication
        actions.append(TransitionAction(
            action_type="communicate",
            description="Announce restructuring vision to organization — context and timeline",
            owner="Leadership",
            cost_estimate=5_000,
            duration_weeks=1,
            priority="Critical",
        ))

        # Knowledge documentation for nexus employees
        if nexus_ids:
            actions.append(TransitionAction(
                action_type="document",
                description=(
                    f"Knowledge capture sessions for {len(nexus_ids)} Nexus employees "
                    "— document critical processes, dependencies, and tribal knowledge"
                ),
                owner="HR",
                cost_estimate=len(nexus_ids) * 2_500,
                duration_weeks=6,
                priority="Critical",
                dependencies=["Announce restructuring vision"],
            ))

        # Recruitment planning
        if fa.n_external_hires > 0:
            actions.append(TransitionAction(
                action_type="communicate",
                description=(
                    f"Finalize job descriptions and open {fa.n_external_hires} "
                    "external requisitions with Recruiting"
                ),
                owner="HR",
                cost_estimate=3_000,
                duration_weeks=2,
                priority="High",
            ))

        # Training assessment
        if fa.internal_fills:
            actions.append(TransitionAction(
                action_type="train",
                description=(
                    f"Skills assessment interviews with {len(fa.internal_fills)} "
                    "internal transition candidates — confirm role fit and training plan"
                ),
                owner="HR",
                cost_estimate=len(fa.internal_fills) * 500,
                duration_weeks=3,
                priority="High",
            ))

        # Severance planning
        if n_exits > 0:
            actions.append(TransitionAction(
                action_type="communicate",
                description=(
                    f"Prepare individual severance packages and WARN notice "
                    f"for {n_exits} impacted positions"
                ),
                owner="HR",
                cost_estimate=fa.severance_cost * 0.03,  # legal + admin costs
                duration_weeks=4,
                priority="Critical",
                dependencies=["Announce restructuring vision"],
            ))

        # Budget approval
        actions.append(TransitionAction(
            action_type="communicate",
            description="Secure budget approval for transition program from Finance",
            owner="Finance",
            cost_estimate=0,
            duration_weeks=2,
            priority="Critical",
        ))

        phase_cost = sum(a.cost_estimate for a in actions)
        risk = "High" if n_exits > 5 or len(nexus_ids) > 2 else "Medium"

        return TransitionPhase(
            name="Phase 1: Foundation",
            months_start=0,
            months_end=3,
            theme="Communicate, document, and prepare",
            actions=actions,
            headcount_change=0,
            cost_estimate=phase_cost,
            risk_level=risk,
        )

    def _phase2_execution(
        self,
        fa: FutureStateAnalysis,
        sa: Optional[SkillsGapAnalysis],
        n_hires: int,
        n_trains: int,
    ) -> TransitionPhase:
        """Phase 2 (months 3–9): Execution — hire, train, restructure."""
        actions: list[TransitionAction] = []

        # External hiring
        if n_hires > 0:
            actions.append(TransitionAction(
                action_type="hire",
                description=f"Execute {n_hires} external hire(s) across target teams",
                owner="HR",
                cost_estimate=fa.hiring_cost,
                duration_weeks=16,
                priority="Critical",
            ))

        # Internal transitions and training
        if fa.internal_fills:
            actions.append(TransitionAction(
                action_type="train",
                description=(
                    f"Launch training programs for {n_trains} internal transition "
                    "candidates — role-specific upskilling and onboarding to new teams"
                ),
                owner="Engineering",
                cost_estimate=fa.training_cost,
                duration_weeks=12,
                priority="High",
                dependencies=["Execute external hire"],
            ))

        # Skills training from gap analysis
        if sa:
            critical_gaps = [g for g in sa.gaps if g.severity in ("Critical", "High") and g.gap < 0]
            if critical_gaps:
                actions.append(TransitionAction(
                    action_type="train",
                    description=(
                        f"Launch structured training for {len(critical_gaps)} critical "
                        f"skill gaps — priority: "
                        f"{', '.join(g.skill_name for g in critical_gaps[:3])}"
                    ),
                    owner="Engineering",
                    cost_estimate=sum(g.build_cost_total for g in critical_gaps),
                    duration_weeks=20,
                    priority="High",
                ))

        # Org structure changes
        actions.append(TransitionAction(
            action_type="restructure",
            description=(
                f"Implement team restructuring — transition to "
                f"{fa.design.name} target structure"
            ),
            owner="Leadership",
            cost_estimate=0,
            duration_weeks=8,
            priority="High",
            dependencies=["Launch training programs"],
        ))

        # Progress check
        actions.append(TransitionAction(
            action_type="communicate",
            description="Mid-transition all-hands: progress update, Q&A, morale check",
            owner="Leadership",
            cost_estimate=2_000,
            duration_weeks=1,
            priority="Medium",
        ))

        phase_cost = sum(a.cost_estimate for a in actions)
        risk = "High" if n_hires > 10 else "Medium"

        return TransitionPhase(
            name="Phase 2: Execution",
            months_start=3,
            months_end=9,
            theme="Hire, train, and restructure",
            actions=actions,
            headcount_change=n_hires - len([
                f for f in fa.internal_fills
                if not f.skill_gap  # no-gap fills = lateral moves, not net additions
            ]),
            cost_estimate=phase_cost,
            risk_level=risk,
        )

    def _phase3_stabilisation(
        self,
        fa: FutureStateAnalysis,
        sa: Optional[SkillsGapAnalysis],
    ) -> TransitionPhase:
        """Phase 3 (months 9–24): Stabilisation — optimise and embed."""
        actions: list[TransitionAction] = []

        # Performance calibration
        actions.append(TransitionAction(
            action_type="communicate",
            description=(
                "First performance cycle in new structure — recalibrate goals, "
                "OKRs, and team rituals"
            ),
            owner="HR",
            cost_estimate=5_000,
            duration_weeks=6,
            priority="High",
        ))

        # Skills certification
        if sa and any(g.gap < 0 for g in sa.gaps):
            actions.append(TransitionAction(
                action_type="train",
                description="Skills certification and proficiency validation for trained employees",
                owner="Engineering",
                cost_estimate=sum(g.build_cost_total * 0.1 for g in sa.gaps if g.gap < 0),
                duration_weeks=8,
                priority="Medium",
            ))

        # Retention check
        actions.append(TransitionAction(
            action_type="communicate",
            description=(
                "Post-transition retention survey and 1:1 check-ins — "
                "identify flight risks from restructuring fatigue"
            ),
            owner="HR",
            cost_estimate=3_000,
            duration_weeks=3,
            priority="High",
        ))

        # Process documentation
        actions.append(TransitionAction(
            action_type="document",
            description=(
                "Update all runbooks, handbooks, and process documentation "
                "to reflect new org structure"
            ),
            owner="Engineering",
            cost_estimate=8_000,
            duration_weeks=10,
            priority="Medium",
        ))

        # Final review
        actions.append(TransitionAction(
            action_type="communicate",
            description=(
                "Transition retrospective with leadership — measure outcomes vs plan, "
                "document lessons learned"
            ),
            owner="Leadership",
            cost_estimate=2_000,
            duration_weeks=1,
            priority="Low",
        ))

        phase_cost = sum(a.cost_estimate for a in actions)

        return TransitionPhase(
            name="Phase 3: Stabilisation",
            months_start=9,
            months_end=24,
            theme="Embed, optimise, and measure",
            actions=actions,
            headcount_change=0,
            cost_estimate=phase_cost,
            risk_level="Low",
        )

    # ------------------------------------------------------------------
    # Risk assessment
    # ------------------------------------------------------------------

    def _assess_risks(
        self,
        fa: FutureStateAnalysis,
        sa: Optional[SkillsGapAnalysis],
        nexus_ids: set[str],
        n_exits: int,
        n_hires: int,
    ) -> list[TransitionRisk]:
        risks = []

        if nexus_ids and n_exits > 0:
            risks.append(TransitionRisk(
                category="knowledge_loss",
                description=(
                    f"{len(nexus_ids)} Nexus employee(s) represent critical knowledge "
                    "concentration. Departure without documentation causes irreversible loss."
                ),
                probability="High",
                impact="High",
                mitigation=(
                    "Mandate knowledge capture sessions before Phase 2. "
                    "Assign shadow roles for critical processes."
                ),
            ))

        if n_exits > 0:
            risks.append(TransitionRisk(
                category="retention",
                description=(
                    f"Restructuring announcement may trigger voluntary departures "
                    f"beyond planned {n_exits} exits — survivor syndrome effect."
                ),
                probability="Medium",
                impact="High",
                mitigation=(
                    "Communicate retention commitments early. "
                    "Offer stay bonuses to critical talent. "
                    "Fast-track career conversations for key individuals."
                ),
            ))

        if n_hires > 5:
            risks.append(TransitionRisk(
                category="productivity",
                description=(
                    f"{n_hires} external hires take 3–6 months to reach full productivity. "
                    "Team output will dip during onboarding."
                ),
                probability="High",
                impact="Medium",
                mitigation=(
                    "Stagger hire start dates to spread onboarding load. "
                    "Assign dedicated onboarding buddies. "
                    "Temporarily reduce delivery commitments during peak onboarding."
                ),
            ))

        if sa and sa.n_critical_gaps > 0:
            risks.append(TransitionRisk(
                category="knowledge_loss",
                description=(
                    f"{sa.n_critical_gaps} critical skill gap(s) mean the org will "
                    "operate below capability in these areas during the transition."
                ),
                probability="Medium",
                impact="High",
                mitigation=(
                    "Contract specialists for critical skill gaps during the training period. "
                    "Prioritise hiring for Critical-rated gaps over Build paths."
                ),
            ))

        risks.append(TransitionRisk(
            category="cultural",
            description=(
                "Restructuring changes team boundaries and reporting lines, "
                "disrupting established trust and collaboration patterns."
            ),
            probability="Medium",
            impact="Medium",
            mitigation=(
                "Preserve existing team clusters where possible in the new structure. "
                "Schedule cross-team offsites within 30 days of restructure completion."
            ),
        ))

        return risks

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _knowledge_loss_risk(
        self, nexus_ids: set[str], n_exits: int, n_current: int
    ) -> str:
        nexus_at_risk = len(nexus_ids) > 0 and n_exits > 0
        exit_rate = n_exits / max(n_current, 1)
        if nexus_at_risk or exit_rate > 0.20:
            return "High"
        if exit_rate > 0.05:
            return "Medium"
        return "Low"

    def _productivity_dip(
        self, n_exits: int, n_hires: int, n_current: int
    ) -> float:
        """Estimated peak productivity dip (%) during Phase 2."""
        if n_current == 0:
            return 0.0
        # Exits cause immediate dip; hires cause onboarding lag
        exit_dip  = (n_exits  / n_current) * 0.80
        hire_lag  = (n_hires  / max(n_current, 1)) * 0.40
        return min(round((exit_dip + hire_lag) * 100, 1), 40.0)

    def _executive_summary(
        self,
        fa: FutureStateAnalysis,
        n_hires: int,
        n_exits: int,
        n_trains: int,
        total_cost: float,
        knowledge_risk: str,
        productivity_dip: float,
    ) -> str:
        cost_delta = fa.delta_vs_current
        direction = "increase" if cost_delta > 0 else "reduction"
        return (
            f"The proposed transition to **{fa.design.name}** spans approximately "
            f"**{fa.months_to_target} months** across three phases. "
            f"It requires **{n_hires} external hire(s)**, "
            f"**{n_trains} internal transition(s)**, and "
            f"**{n_exits} position(s)** that will not be retained in the new structure. "
            f"\n\n"
            f"Estimated annual operating cost after transition: "
            f"**${fa.estimated_annual_cost:,.0f}** — "
            f"a **${abs(cost_delta):,.0f} {direction}** vs current. "
            f"Total one-time transition investment: **${total_cost:,.0f}**. "
            f"\n\n"
            f"Key risk: **{knowledge_risk} knowledge loss risk** — "
            f"peak productivity impact estimated at **{productivity_dip:.0f}%** during Phase 2."
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def plan_transition(
    future_analysis: FutureStateAnalysis,
    skills_analysis: Optional[SkillsGapAnalysis] = None,
    current_employees_df: Optional[pd.DataFrame] = None,
    nexus_ids: Optional[set[str]] = None,
) -> TransitionPlan:
    """Generate a workforce transition plan. Convenience wrapper."""
    if current_employees_df is None:
        current_employees_df = pd.DataFrame()
    return TransitionPlanner().plan(
        future_analysis, skills_analysis, current_employees_df, nexus_ids
    )
