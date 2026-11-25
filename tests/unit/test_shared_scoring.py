"""Shared impact scoring (backend/services/scoring.py).

Regression for the per-service heuristic impact = 70·salary_percentile + 15·nexus + noise,
which made impact a near-copy of pay and let the optimizer keep leaders just for being
well paid.
"""

import networkx as nx
import pandas as pd
import pytest

from backend.routers.v1 import _scored_df
from backend.services import ohi_service, resilience_service
from backend.services.data_service import build_dashboard_data, get_org, run_simulation
from backend.services.scoring import add_scores, org_impact_scores
from models.network_analysis import _LARGE_GRAPH_THRESHOLD, compute_centrality_metrics


@pytest.mark.parametrize("scenario", ["A", "B", "C"])
def test_impact_is_no_longer_a_copy_of_salary(scenario):
    df = add_scores(get_org(scenario, "small").employees.reset_index(drop=True))
    rho = df["impact_score"].corr(df["annual_salary"], method="spearman")
    assert rho < 0.85          # was ~0.99 with the salary-rank heuristic
    assert df["impact_score"].between(0, 100).all()


def test_every_surface_reports_the_same_impact_score():
    org = get_org("A", "small")
    ref = org_impact_scores(org)
    short_to_full = {str(e)[:8].upper(): str(e) for e in org.employees["employee_id"]}

    dash = {short_to_full[r["employee_id"]]: r["impact_score"] for r in build_dashboard_data("A", "small")["employee_table"]}
    ohi = ohi_service._add_scores(org.employees.reset_index(drop=True)).set_index("employee_id")["impact_score"]
    v1 = _scored_df("A", "small").set_index("employee_id")["impact_score"]

    for eid, score in ref.items():
        assert dash[eid] == score
        assert ohi[eid] == score
        assert v1[eid] == score


def test_scores_are_cached_per_org_object():
    org = get_org("B", "small")
    assert org_impact_scores(org) is org_impact_scores(org)


def test_leadership_toggle_matters_at_the_default_budget():
    """With pay-independent impact, leaders are no longer kept 'for free' at 80%."""
    off = run_simulation("A", "small", 80, [], [], False, False)["constraints"]["leadership"]
    on = run_simulation("A", "small", 80, [], [], True, False)["constraints"]["leadership"]
    assert off["covered"] < off["total"]
    assert on["covered"] == on["total"]


def test_poaching_scenario_selects_top_impact_band_by_default():
    df = resilience_service._add_scores(get_org("A", "medium").employees.reset_index(drop=True))
    result = resilience_service.run_disruption_scenario(df, "competitive_poaching", {"n": 8})
    # An absolute ">= 65" cut-off selected only ~3 people on the new score scale
    assert result["primary_count"] == 8


def test_large_graph_uses_sampled_betweenness_and_scores_every_employee():
    n = _LARGE_GRAPH_THRESHOLD + 100
    G = nx.relabel_nodes(nx.barabasi_albert_graph(n, 2, seed=1), str)
    nx.set_edge_attributes(G, 1.0, "weight")
    employees = pd.DataFrame({"employee_id": [str(i) for i in range(n)]})
    cent = compute_centrality_metrics(G, employees)
    assert len(cent) == n
    assert cent["betweenness_centrality"].max() > 0
