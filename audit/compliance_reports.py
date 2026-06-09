"""Compliance report generation for EIBO audit system.

Produces GDPR data processing reports, access summaries, and model
decision impact reports suitable for regulatory audit submissions.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from audit.logger import EventCategory
from audit.trail_viewer import TrailViewer

# ---------------------------------------------------------------------------
# Report dataclasses
# ---------------------------------------------------------------------------

class ComplianceReport:
    """Base class for compliance report output."""

    def __init__(self, title: str, generated_at: str, sections: list[dict]) -> None:
        self.title        = title
        self.generated_at = generated_at
        self.sections     = sections   # list of {"heading": str, "content": str|pd.DataFrame}

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", f"*Generated: {self.generated_at} UTC*", ""]
        for sec in self.sections:
            lines.append(f"## {sec['heading']}")
            content = sec["content"]
            if isinstance(content, pd.DataFrame):
                if content.empty:
                    lines.append("*No data available.*")
                else:
                    lines.append(content.to_markdown(index=False))
            else:
                lines.append(str(content))
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

class ComplianceReportGenerator:
    """Generates compliance and audit reports from event data."""

    def __init__(self, viewer: TrailViewer | None = None) -> None:
        self._viewer = viewer or TrailViewer()

    # ------------------------------------------------------------------
    # GDPR data processing report
    # ------------------------------------------------------------------

    def gdpr_data_processing_report(self, days_back: int = 30) -> ComplianceReport:
        """Generate GDPR Article 30 compliant data processing activity report."""
        hours = days_back * 24
        access_df = self._viewer.events_df(
            category=EventCategory.ACCESS, hours_back=hours, limit=10_000
        )
        export_df = self._viewer.events_df(
            category=EventCategory.EXPORT, hours_back=hours, limit=10_000
        )
        auth_df = self._viewer.events_df(
            category=EventCategory.AUTH, hours_back=hours, limit=5_000
        )
        failure_df = self._viewer.failure_summary(hours_back=hours)

        # Summary counts
        summary = pd.DataFrame([{
            "Metric": "Data access events",
            "Count":  len(access_df),
        }, {
            "Metric": "Export events",
            "Count":  len(export_df),
        }, {
            "Metric": "Authentication events",
            "Count":  len(auth_df),
        }, {
            "Metric": "Failed access attempts",
            "Count":  len(self._viewer.events_df(
                hours_back=hours, outcome="failure", limit=5_000
            )),
        }])

        # Unique data subjects accessed
        unique_resources = (
            access_df["resource"].nunique() if not access_df.empty else 0
        )

        # Users who exported data
        exporters = (
            export_df[["user_email", "user_role", "resource", "timestamp"]]
            .drop_duplicates()
            if not export_df.empty
            else pd.DataFrame()
        )

        sections = [
            {
                "heading": "Scope",
                "content": (
                    f"Report covers the last **{days_back} days** of platform activity.\n\n"
                    "**Data Controller:** EIBO Platform (on-premises deployment)\n"
                    "**Processing Purpose:** Workforce planning and budget optimisation\n"
                    "**Legal Basis:** Legitimate interest (organisational management)\n"
                    "**Data Retention:** Configurable per data type (default: 365 days audit, 90 days simulations)"
                ),
            },
            {
                "heading": "Activity Summary",
                "content": summary,
            },
            {
                "heading": "Data Access",
                "content": (
                    f"**{len(access_df)}** data access events recorded.\n"
                    f"**{unique_resources}** unique resources accessed.\n\n"
                    + (self._viewer.activity_by_user(hours_back=hours).to_markdown(index=False)
                       if not access_df.empty else "*No access events.*")
                ),
            },
            {
                "heading": "Data Exports",
                "content": exporters if not exporters.empty else "*No export events.*",
            },
            {
                "heading": "Failed Access Attempts",
                "content": failure_df if not failure_df.empty else "*No failed attempts.*",
            },
            {
                "heading": "Data Subject Rights",
                "content": (
                    "All personally identifiable data is subject to the following rights:\n"
                    "- **Right of access**: HR Administrators can provide data extracts on request\n"
                    "- **Right to rectification**: Data sourced from HRIS; corrections apply at source\n"
                    "- **Right to erasure**: Anonymisation pipeline available for long-term archival\n"
                    "- **Right to portability**: All records exportable as CSV/JSON\n"
                    "- **Automated decision-making**: Platform is decision-support only; "
                    "no decisions are automated. Human override required for all retention recommendations."
                ),
            },
        ]

        return ComplianceReport(
            title=f"GDPR Data Processing Activity Report ({days_back}-day window)",
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            sections=sections,
        )

    # ------------------------------------------------------------------
    # Access summary report
    # ------------------------------------------------------------------

    def access_summary_report(self, days_back: int = 7) -> ComplianceReport:
        """Who accessed what data in the past N days."""
        hours = days_back * 24
        activity = self._viewer.activity_by_user(hours_back=hours)
        self._viewer.event_volume_by_hour(hours_back=hours)
        security = self._viewer.security_events(hours_back=hours)

        # Privilege summary by role
        access_df = self._viewer.events_df(
            category=EventCategory.ACCESS, hours_back=hours, limit=10_000
        )
        by_role = pd.DataFrame()
        if not access_df.empty:
            by_role = (
                access_df.groupby("user_role")
                .agg(users=("user_email", "nunique"), events=("event_id", "count"))
                .reset_index()
            )

        sections = [
            {
                "heading": "Scope",
                "content": f"Data access summary for the last **{days_back} days**.",
            },
            {
                "heading": "User Activity",
                "content": activity if not activity.empty else "*No activity recorded.*",
            },
            {
                "heading": "Access by Role",
                "content": by_role if not by_role.empty else "*No access events.*",
            },
            {
                "heading": "Security Events",
                "content": (
                    security[["timestamp", "user_email", "action", "resource", "detail"]]
                    if not security.empty else "*No security events.*"
                ),
            },
        ]

        return ComplianceReport(
            title=f"Data Access Summary Report ({days_back}-day window)",
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            sections=sections,
        )

    # ------------------------------------------------------------------
    # Model decision impact report
    # ------------------------------------------------------------------

    def model_decision_report(self, days_back: int = 30) -> ComplianceReport:
        """Algorithmic accountability report: simulations and overrides."""
        hours = days_back * 24
        sim_df = self._viewer.events_df(
            category=EventCategory.SIMULATION, hours_back=hours, limit=5_000
        )
        override_df = self._viewer.events_df(
            category=EventCategory.OVERRIDE, hours_back=hours, limit=5_000
        )

        override_rate = (
            round(len(override_df) / max(len(sim_df), 1) * 100, 1)
            if len(sim_df) > 0 else 0.0
        )

        sections = [
            {
                "heading": "Scope",
                "content": (
                    f"Algorithmic decision report for the last **{days_back} days**.\n\n"
                    "This report documents all model-driven simulation runs and the human "
                    "overrides applied, in compliance with algorithmic accountability requirements."
                ),
            },
            {
                "heading": "Simulation Activity",
                "content": (
                    f"**{len(sim_df)}** simulation runs recorded.\n\n"
                    + (sim_df[["timestamp", "user_email", "resource", "detail"]]
                       .head(50).to_markdown(index=False)
                       if not sim_df.empty else "*No simulation runs.*")
                ),
            },
            {
                "heading": "Human Overrides",
                "content": (
                    f"**{len(override_df)}** override events recorded "
                    f"(**{override_rate}%** override rate vs simulation count).\n\n"
                    + (override_df[["timestamp", "user_email", "resource", "detail"]]
                       .head(50).to_markdown(index=False)
                       if not override_df.empty else "*No overrides recorded.*")
                ),
            },
            {
                "heading": "Algorithmic Accountability Statement",
                "content": (
                    "The EIBO platform is classified as a **decision-support tool**, not an "
                    "autonomous decision-making system:\n\n"
                    "- All recommendations are generated by an Integer Linear Programming model "
                    "maximising workforce impact under budget constraints.\n"
                    "- No employee is retained or excluded without explicit human confirmation.\n"
                    "- Every simulation result can be overridden by authorised personnel.\n"
                    "- All model inputs (impact scores, attrition probabilities) include SHAP "
                    "explainability so decision-makers understand the basis of each recommendation.\n"
                    "- Fairness audits are run periodically to detect demographic bias in impact scores."
                ),
            },
        ]

        return ComplianceReport(
            title=f"Model Decision Impact Report ({days_back}-day window)",
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            sections=sections,
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def generate_gdpr_report(days_back: int = 30) -> ComplianceReport:
    return ComplianceReportGenerator().gdpr_data_processing_report(days_back)


def generate_access_report(days_back: int = 7) -> ComplianceReport:
    return ComplianceReportGenerator().access_summary_report(days_back)


def generate_model_report(days_back: int = 30) -> ComplianceReport:
    return ComplianceReportGenerator().model_decision_report(days_back)
