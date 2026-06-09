"""Data Pipeline Workflow — Bronze → Silver → Gold ingestion flow.

Orchestrates data ingestion, cleansing, aggregation, and validation.
Registers itself with the WorkflowRegistry on import.
"""

from __future__ import annotations

import logging
import time

from workflows.engine import FlowRun, TaskResult, flow, get_registry, task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@task(name="ingest_bronze", retries=2, retry_delay=2.0)
def ingest_bronze(source_path: str = "demo") -> dict:
    """Ingest raw data into the Bronze layer."""
    time.sleep(0.05)  # simulate I/O
    record_count = 487 if source_path == "demo" else 0
    logger.info("Bronze ingestion complete: %d records", record_count)
    return {"records_ingested": record_count, "source": source_path}


@task(name="cleanse_silver", retries=1)
def cleanse_silver(bronze_result: dict) -> dict:
    """Cleanse and normalise Silver layer data."""
    time.sleep(0.03)
    records = bronze_result.get("records_ingested", 0)
    clean   = max(records - 3, 0)  # simulate 3 records dropped
    logger.info("Silver cleanse: %d → %d records", records, clean)
    return {"records_clean": clean, "records_dropped": records - clean}


@task(name="aggregate_gold", retries=1)
def aggregate_gold(silver_result: dict) -> dict:
    """Aggregate Gold layer materialized views."""
    time.sleep(0.04)
    records = silver_result.get("records_clean", 0)
    logger.info("Gold aggregation: %d records", records)
    return {"records_aggregated": records, "views_refreshed": 8}


@task(name="validate_pipeline")
def validate_pipeline(gold_result: dict) -> dict:
    """Run data quality validation on Gold layer."""
    time.sleep(0.02)
    views = gold_result.get("views_refreshed", 0)
    passed = views
    logger.info("Validation: %d/%d views passed", passed, views)
    return {"checks_passed": passed, "checks_failed": 0}


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

@flow(
    name="data_pipeline",
    description="Bronze → Silver → Gold ingestion pipeline with validation",
    tags=["data", "pipeline", "scheduled"],
)
def data_pipeline_flow(source_path: str = "demo", _flow_run: FlowRun | None = None) -> None:
    r1: TaskResult = ingest_bronze(source_path=source_path)
    if _flow_run:
        _flow_run.task_results.append(r1)

    if r1.failed:
        logger.error("Pipeline aborted: bronze ingestion failed")
        return

    r2: TaskResult = cleanse_silver(bronze_result=r1.result)
    if _flow_run:
        _flow_run.task_results.append(r2)

    r3: TaskResult = aggregate_gold(silver_result=r2.result if r2.succeeded else {})
    if _flow_run:
        _flow_run.task_results.append(r3)

    r4: TaskResult = validate_pipeline(gold_result=r3.result if r3.succeeded else {})
    if _flow_run:
        _flow_run.task_results.append(r4)


# Register on import
get_registry().register(data_pipeline_flow)
