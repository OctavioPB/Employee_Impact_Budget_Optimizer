"""Shared employee scoring for every service and the public v1 API.

impact_score
    models.impact_scorer: 100 × (0.40·KPI + 0.30·network + 0.20·skills + 0.10·cost),
    computed from the org's performance history, collaboration graph and skills.
    Replaces the old per-service heuristic (70·salary_percentile + 15·nexus + noise),
    which made impact a near-copy of pay (Spearman ≈ 0.99 with salary).

attrition_risk
    Unchanged demo heuristic: 0.6·(1 − salary_percentile) + U(0, 0.4) − 0.15·nexus.
    The random draws happen in the same order as before, so every attrition value
    in the app is identical to what it was before impact scoring moved here.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from models.impact_scorer import compute_impact_scores
from models.network_analysis import build_graph, compute_centrality_metrics

if TYPE_CHECKING:
    from demo_data.generator import GeneratedOrg

# Keyed by id(org); the org itself is kept in the entry so an id is never reused
# while cached. Bounded: 9 demo orgs plus a few custom ones from /admin/demo/generate.
_IMPACT_CACHE: OrderedDict[int, tuple[GeneratedOrg, pd.Series]] = OrderedDict()
_CACHE_SIZE = 12


def org_impact_scores(org: GeneratedOrg) -> pd.Series:
    """Impact score (0-100, 1 decimal) per employee_id, computed once per org object."""
    hit = _IMPACT_CACHE.get(id(org))
    if hit is not None and hit[0] is org:
        _IMPACT_CACHE.move_to_end(id(org))
        return hit[1]

    centrality = compute_centrality_metrics(build_graph(org.collaboration), org.employees)
    result = compute_impact_scores(
        employees_df=org.employees,
        performance_df=org.performance,
        centrality_df=centrality,
        employee_skills_df=org.employee_skills,
        skills_df=org.skills,
    )
    scores = (
        result.scores.assign(employee_id=result.scores["employee_id"].astype(str))
        .set_index("employee_id")["impact_score"]
        .astype(float)
        .round(1)
    )

    _IMPACT_CACHE[id(org)] = (org, scores)
    while len(_IMPACT_CACHE) > _CACHE_SIZE:
        _IMPACT_CACHE.popitem(last=False)
    return scores


def impact_for(df: pd.DataFrame, org: GeneratedOrg) -> pd.Series:
    """Impact scores aligned to df's rows (employees missing from the scorer get the median)."""
    scores = org_impact_scores(org)
    return df["employee_id"].astype(str).map(scores).fillna(float(scores.median())).round(1)


def _org_for(df: pd.DataFrame) -> GeneratedOrg:
    from backend.services.data_service import (
        get_org,  # local import: data_service imports this module
    )

    return get_org(str(df["scenario_id"].iloc[0]).upper(), str(df["org_size"].iloc[0]).lower())


def add_scores(df: pd.DataFrame, org: GeneratedOrg | None = None) -> pd.DataFrame:
    """Return a copy of an employees frame with impact_score and attrition_risk added.

    The org is looked up from the frame's scenario_id / org_size columns when not given,
    which also picks up custom orgs generated through /api/admin/demo/generate.
    """
    org = org if org is not None else _org_for(df)
    rng = np.random.default_rng(42)
    sal_rank = df["annual_salary"].rank(pct=True)
    rng.normal(0, 5, len(df))  # former impact noise: drawn so the attrition draws below are unchanged

    df = df.copy()
    df["impact_score"] = impact_for(df, org)

    nexus_r = df["_is_nexus"].astype(float) * 0.15
    attr_raw = (1 - sal_rank) * 0.6 + rng.uniform(0, 0.4, len(df)) - nexus_r
    df["attrition_risk"] = np.clip(attr_raw, 0.01, 0.99).round(3)
    return df
