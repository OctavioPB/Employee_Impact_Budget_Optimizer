"""Model Retraining Workflow — drift detection → retraining → validation → deploy.

Registered with the WorkflowRegistry on import.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from workflows.engine import FlowRun, TaskResult, flow, get_registry, task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@task(name="assess_model_drift")
def assess_model_drift(model_name: str = "impact_scorer") -> dict:
    """Check model performance metrics for drift."""
    time.sleep(0.04)
    drift_score = 0.12  # simulated
    requires_retrain = drift_score > 0.10
    logger.info("Drift assessment for '%s': score=%.2f, retrain=%s",
                model_name, drift_score, requires_retrain)
    return {"drift_score": drift_score, "requires_retrain": requires_retrain,
            "model_name": model_name}


@task(name="retrain_model", retries=1, retry_delay=5.0)
def retrain_model(drift_result: dict) -> dict:
    """Retrain the model on current gold-layer data."""
    time.sleep(0.08)
    model_name = drift_result.get("model_name", "unknown")
    new_auc    = 0.847
    logger.info("Model '%s' retrained: AUC=%.3f", model_name, new_auc)
    return {"model_name": model_name, "new_auc": new_auc,
            "training_samples": 487, "validation_samples": 122}


@task(name="validate_model")
def validate_model(train_result: dict) -> dict:
    """Validate retrained model against holdout set."""
    time.sleep(0.03)
    auc       = train_result.get("new_auc", 0.0)
    threshold = 0.75
    passed    = auc >= threshold
    logger.info("Model validation: AUC=%.3f (threshold %.2f): %s",
                auc, threshold, "PASS" if passed else "FAIL")
    return {"auc": auc, "threshold": threshold, "passed": passed}


@task(name="deploy_model")
def deploy_model(validation_result: dict) -> dict:
    """Promote validated model to production."""
    time.sleep(0.02)
    if not validation_result.get("passed"):
        raise ValueError("Model validation failed — not deploying.")
    logger.info("Model deployed to production.")
    return {"deployed": True, "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}


@task(name="notify_retraining_complete")
def notify_retraining_complete(deploy_result: dict) -> dict:
    """Send post-retraining notification."""
    time.sleep(0.01)
    return {"notification_sent": deploy_result.get("deployed", False)}


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

@flow(
    name="model_retraining",
    description="Drift detection → retraining → validation → production deployment",
    tags=["ml", "models", "scheduled"],
)
def model_retraining_flow(
    model_name: str = "impact_scorer",
    force_retrain: bool = False,
    _flow_run: Optional[FlowRun] = None,
) -> None:
    r1: TaskResult = assess_model_drift(model_name=model_name)
    if _flow_run:
        _flow_run.task_results.append(r1)

    if r1.failed:
        return

    if not force_retrain and not r1.result.get("requires_retrain"):
        logger.info("No drift detected — skipping retraining")
        return

    r2: TaskResult = retrain_model(drift_result=r1.result)
    if _flow_run:
        _flow_run.task_results.append(r2)
    if r2.failed:
        return

    r3: TaskResult = validate_model(train_result=r2.result)
    if _flow_run:
        _flow_run.task_results.append(r3)
    if r3.failed:
        return

    r4: TaskResult = deploy_model(validation_result=r3.result)
    if _flow_run:
        _flow_run.task_results.append(r4)

    r5: TaskResult = notify_retraining_complete(deploy_result=r4.result if r4.succeeded else {})
    if _flow_run:
        _flow_run.task_results.append(r5)


get_registry().register(model_retraining_flow)
