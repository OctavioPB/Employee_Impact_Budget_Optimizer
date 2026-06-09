"""Lightweight workflow engine — Prefect-compatible DAG API without the dependency.

Provides @task and @flow decorators, TaskResult, FlowRun, and a WorkflowRegistry
for managing and executing named workflows with retry logic, logging, and
status tracking compatible with the EIBO admin UI.

Design intent: drop-in compatible with Prefect 2.x concepts; if Prefect is later
installed, swapping the decorators is the only change required.
"""

from __future__ import annotations

import functools
import logging
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State enums
# ---------------------------------------------------------------------------

class TaskState(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    RETRYING  = "retrying"
    SKIPPED   = "skipped"


class FlowState(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CRASHED   = "crashed"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    task_name:   str
    state:       TaskState
    result:      Any       = None
    error:       str       = ""
    started_at:  str       = ""
    finished_at: str       = ""
    duration_s:  float     = 0.0
    attempt:     int       = 1

    @property
    def succeeded(self) -> bool:
        return self.state == TaskState.COMPLETED

    @property
    def failed(self) -> bool:
        return self.state == TaskState.FAILED


@dataclass
class FlowRun:
    """Record of a single flow execution."""
    run_id:      str
    flow_name:   str
    state:       FlowState
    started_at:  str
    finished_at: str       = ""
    duration_s:  float     = 0.0
    task_results: list[TaskResult] = field(default_factory=list)
    parameters:  dict      = field(default_factory=dict)
    error:       str       = ""
    triggered_by: str      = "manual"   # "manual" | "schedule" | "api"

    @property
    def succeeded(self) -> bool:
        return self.state == FlowState.COMPLETED

    @property
    def n_tasks(self) -> int:
        return len(self.task_results)

    @property
    def n_failed(self) -> int:
        return sum(1 for t in self.task_results if t.failed)

    def summary(self) -> str:
        return (
            f"Flow '{self.flow_name}' — {self.state.value} "
            f"({self.n_tasks} tasks, {self.n_failed} failed, "
            f"{self.duration_s:.1f}s)"
        )


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

class task:
    """Decorator that wraps a function as a workflow task with retry logic."""

    def __init__(
        self,
        name:        str | None = None,
        retries:     int = 0,
        retry_delay: float = 1.0,
        tags:        list[str] | None = None,
    ) -> None:
        self._name        = name
        self._retries     = retries
        self._retry_delay = retry_delay
        self._tags        = tags or []

    def __call__(self, fn: Callable) -> _TaskWrapper:
        return _TaskWrapper(fn, self._name or fn.__name__,
                             self._retries, self._retry_delay, self._tags)


class _TaskWrapper:
    def __init__(self, fn: Callable, name: str,
                 retries: int, retry_delay: float, tags: list[str]) -> None:
        self._fn          = fn
        self.task_name    = name
        self._retries     = retries
        self._retry_delay = retry_delay
        self._tags        = tags
        functools.update_wrapper(self, fn)

    def __call__(self, *args, **kwargs) -> TaskResult:
        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs) -> TaskResult:
        attempt = 1
        max_attempts = self._retries + 1
        while attempt <= max_attempts:
            started = time.perf_counter()
            started_at = datetime.utcnow().isoformat() + "Z"
            try:
                result = self._fn(*args, **kwargs)
                duration = time.perf_counter() - started
                logger.info("Task '%s' completed (attempt %d, %.2fs)",
                            self.task_name, attempt, duration)
                return TaskResult(
                    task_name=self.task_name, state=TaskState.COMPLETED,
                    result=result, started_at=started_at,
                    finished_at=datetime.utcnow().isoformat() + "Z",
                    duration_s=round(duration, 3), attempt=attempt,
                )
            except Exception as exc:
                duration = time.perf_counter() - started
                err_msg = f"{type(exc).__name__}: {exc}"
                logger.warning("Task '%s' failed (attempt %d/%d): %s",
                               self.task_name, attempt, max_attempts, err_msg)
                if attempt < max_attempts:
                    time.sleep(self._retry_delay)
                    attempt += 1
                else:
                    return TaskResult(
                        task_name=self.task_name, state=TaskState.FAILED,
                        error=err_msg, started_at=started_at,
                        finished_at=datetime.utcnow().isoformat() + "Z",
                        duration_s=round(duration, 3), attempt=attempt,
                    )
        # Unreachable but satisfies type checker
        return TaskResult(task_name=self.task_name, state=TaskState.FAILED)  # pragma: no cover


class flow:
    """Decorator that wraps a function as a named workflow flow."""

    def __init__(
        self,
        name:        str | None = None,
        description: str = "",
        tags:        list[str] | None = None,
    ) -> None:
        self._name        = name
        self._description = description
        self._tags        = tags or []

    def __call__(self, fn: Callable) -> _FlowWrapper:
        return _FlowWrapper(fn, self._name or fn.__name__,
                             self._description, self._tags)


class _FlowWrapper:
    def __init__(self, fn: Callable, name: str,
                 description: str, tags: list[str]) -> None:
        self._fn          = fn
        self.flow_name    = name
        self.description  = description
        self._tags        = tags
        self._run_history: list[FlowRun] = []
        functools.update_wrapper(self, fn)

    def __call__(self, *args, triggered_by: str = "manual", **kwargs) -> FlowRun:
        return self.run(*args, triggered_by=triggered_by, **kwargs)

    def run(self, *args, triggered_by: str = "manual", **kwargs) -> FlowRun:
        run_id     = str(uuid4())
        started    = time.perf_counter()
        started_at = datetime.utcnow().isoformat() + "Z"
        run = FlowRun(
            run_id=run_id, flow_name=self.flow_name,
            state=FlowState.RUNNING, started_at=started_at,
            parameters=kwargs, triggered_by=triggered_by,
        )
        logger.info("Flow '%s' started (run_id=%s)", self.flow_name, run_id)
        try:
            # Inject the run record so tasks can append results
            kwargs["_flow_run"] = run
            self._fn(*args, **kwargs)
            duration = time.perf_counter() - started
            run.state       = FlowState.COMPLETED
            run.finished_at = datetime.utcnow().isoformat() + "Z"
            run.duration_s  = round(duration, 3)
            logger.info("Flow '%s' completed in %.2fs", self.flow_name, duration)
        except Exception as exc:
            duration = time.perf_counter() - started
            run.state       = FlowState.FAILED
            run.error       = traceback.format_exc()
            run.finished_at = datetime.utcnow().isoformat() + "Z"
            run.duration_s  = round(duration, 3)
            logger.error("Flow '%s' failed: %s", self.flow_name, exc)
        self._run_history.append(run)
        return run

    @property
    def last_run(self) -> FlowRun | None:
        return self._run_history[-1] if self._run_history else None

    @property
    def run_history(self) -> list[FlowRun]:
        return list(reversed(self._run_history))


# ---------------------------------------------------------------------------
# Workflow Registry — tracks all flows and runs
# ---------------------------------------------------------------------------

class WorkflowRegistry:
    """Central registry for all defined flows. Singleton per process."""

    _instance: WorkflowRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> WorkflowRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._flows: dict[str, _FlowWrapper] = {}
        return cls._instance

    def register(self, flow_wrapper: _FlowWrapper) -> None:
        self._flows[flow_wrapper.flow_name] = flow_wrapper

    def get(self, name: str) -> _FlowWrapper | None:
        return self._flows.get(name)

    def all_flows(self) -> list[_FlowWrapper]:
        return list(self._flows.values())

    def run_flow(self, name: str, triggered_by: str = "manual",
                 **kwargs) -> FlowRun | None:
        f = self.get(name)
        if f is None:
            logger.error("Flow '%s' not registered", name)
            return None
        return f.run(triggered_by=triggered_by, **kwargs)

    def all_runs(self, limit: int = 50) -> list[FlowRun]:
        runs = []
        for f in self._flows.values():
            runs.extend(f.run_history)
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[:limit]

    def stats(self) -> dict:
        runs = self.all_runs(limit=500)
        return {
            "total_flows":    len(self._flows),
            "total_runs":     len(runs),
            "completed":      sum(1 for r in runs if r.succeeded),
            "failed":         sum(1 for r in runs if not r.succeeded),
        }


def get_registry() -> WorkflowRegistry:
    return WorkflowRegistry()
