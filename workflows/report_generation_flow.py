"""Report Generation Workflow — automated executive and compliance report generation.

Registered with the WorkflowRegistry on import.
"""

from __future__ import annotations

import logging
import time

from workflows.engine import FlowRun, TaskResult, flow, get_registry, task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@task(name="collect_report_data")
def collect_report_data(report_type: str = "weekly_risk") -> dict:
    """Gather data required for the specified report type."""
    time.sleep(0.05)
    data_sources = {
        "weekly_risk":      ["attrition_scores", "early_warnings", "budget_trajectory"],
        "executive_summary": ["impact_scores", "budget_actuals", "headcount", "simulation_results"],
        "gdpr_compliance":  ["audit_log", "access_events", "export_events"],
        "model_performance": ["model_metrics", "shap_attribution", "fairness_audit"],
    }
    sources = data_sources.get(report_type, ["general"])
    logger.info("Collecting %d data sources for '%s' report", len(sources), report_type)
    return {"report_type": report_type, "sources_collected": sources,
            "record_count": 487}


@task(name="generate_report_content")
def generate_report_content(data: dict) -> dict:
    """Generate report sections from collected data."""
    time.sleep(0.06)
    report_type = data.get("report_type", "unknown")
    sections    = max(3, len(data.get("sources_collected", [])))
    logger.info("Report '%s': %d sections generated", report_type, sections)
    return {"report_type": report_type, "sections": sections,
            "word_count": sections * 220, "charts": min(sections, 5)}


@task(name="format_report")
def format_report(content: dict) -> dict:
    """Format report into distributable formats (Markdown + PDF-ready)."""
    time.sleep(0.03)
    logger.info("Report formatted: %d sections, %d charts",
                content.get("sections", 0), content.get("charts", 0))
    return {"formats": ["markdown", "pdf_ready"],
            "file_size_kb": content.get("word_count", 0) // 4}


@task(name="distribute_report")
def distribute_report(format_result: dict, recipients: list[str] | None = None) -> dict:
    """Distribute formatted report to specified recipients."""
    time.sleep(0.02)
    recipients = recipients or ["executive_team"]
    logger.info("Report distributed to %d recipient group(s)", len(recipients))
    return {"distributed_to": recipients, "channels": ["in_app", "email"]}


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

@flow(
    name="report_generation",
    description="Automated report collection → generation → formatting → distribution",
    tags=["reporting", "compliance", "scheduled"],
)
def report_generation_flow(
    report_type: str = "weekly_risk",
    recipients:  list[str] | None = None,
    _flow_run:   FlowRun | None = None,
) -> None:
    r1: TaskResult = collect_report_data(report_type=report_type)
    if _flow_run:
        _flow_run.task_results.append(r1)
    if r1.failed:
        return

    r2: TaskResult = generate_report_content(data=r1.result)
    if _flow_run:
        _flow_run.task_results.append(r2)
    if r2.failed:
        return

    r3: TaskResult = format_report(content=r2.result)
    if _flow_run:
        _flow_run.task_results.append(r3)

    r4: TaskResult = distribute_report(
        format_result=r3.result if r3.succeeded else {},
        recipients=recipients,
    )
    if _flow_run:
        _flow_run.task_results.append(r4)


get_registry().register(report_generation_flow)
