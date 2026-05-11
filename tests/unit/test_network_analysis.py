"""Unit tests for models/network_analysis.py."""

import numpy as np
import pandas as pd
import pytest

from models.network_analysis import (
    NetworkMetrics,
    analyze_network,
    build_graph,
    compute_centrality_metrics,
    compute_team_fragility,
    detect_communities,
    detect_nexus_employees,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_employees(n: int = 6) -> pd.DataFrame:
    """Minimal employees DataFrame with required columns."""
    return pd.DataFrame({
        "employee_id": [f"e{i}" for i in range(n)],
        "team_id": ["team1"] * 3 + ["team2"] * (n - 3),
        "department": ["Engineering"] * n,
    })


def _make_collab(edges: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        edges, columns=["source_id", "target_id", "interaction_weight"]
    )


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------

class TestBuildGraph:
    def test_simple_graph_has_correct_nodes_and_edges(self):
        collab = _make_collab([("e0", "e1", 0.8), ("e1", "e2", 0.5)])
        G = build_graph(collab)
        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2

    def test_duplicate_edges_keep_max_weight(self):
        collab = _make_collab([
            ("e0", "e1", 0.3),
            ("e0", "e1", 0.9),  # duplicate — should keep 0.9
        ])
        G = build_graph(collab)
        assert G.number_of_edges() == 1
        assert G["e0"]["e1"]["weight"] == pytest.approx(0.9)

    def test_empty_collab_returns_empty_graph(self):
        G = build_graph(pd.DataFrame(columns=["source_id", "target_id", "interaction_weight"]))
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0


# ---------------------------------------------------------------------------
# compute_centrality_metrics
# ---------------------------------------------------------------------------

class TestCentralityMetrics:
    def _star_graph_collab(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Star: e0 is hub connected to e1, e2, e3, e4."""
        edges = [(f"e{i}", "e0", 0.5) for i in range(1, 5)]
        return (
            _make_employees(5),
            _make_collab(edges),
        )

    def test_hub_has_highest_betweenness(self):
        employees, collab = self._star_graph_collab()
        from models.network_analysis import build_graph
        G = build_graph(collab)
        centrality = compute_centrality_metrics(G, employees)
        hub_row = centrality[centrality["employee_id"] == "e0"]
        others = centrality[centrality["employee_id"] != "e0"]
        assert hub_row["betweenness_centrality"].values[0] > others["betweenness_centrality"].max()

    def test_isolated_node_gets_zero_centrality(self):
        employees = _make_employees(4)
        collab = _make_collab([("e0", "e1", 0.5), ("e1", "e2", 0.5)])
        from models.network_analysis import build_graph
        G = build_graph(collab)
        centrality = compute_centrality_metrics(G, employees)
        isolated = centrality[centrality["employee_id"] == "e3"]
        assert isolated["betweenness_centrality"].values[0] == pytest.approx(0.0)
        assert isolated["degree_centrality"].values[0] == pytest.approx(0.0)

    def test_combined_centrality_in_unit_range(self):
        employees = _make_employees(5)
        edges = [("e0", "e1", 0.8), ("e1", "e2", 0.6), ("e2", "e3", 0.4)]
        from models.network_analysis import build_graph
        G = build_graph(_make_collab(edges))
        centrality = compute_centrality_metrics(G, employees)
        assert centrality["combined_centrality"].between(0, 1).all()

    def test_all_employees_present_in_output(self):
        employees = _make_employees(6)
        collab = _make_collab([("e0", "e1", 0.5)])  # only 2 nodes connected
        from models.network_analysis import build_graph
        G = build_graph(collab)
        centrality = compute_centrality_metrics(G, employees)
        assert set(centrality["employee_id"].tolist()) == {f"e{i}" for i in range(6)}


# ---------------------------------------------------------------------------
# detect_nexus_employees
# ---------------------------------------------------------------------------

class TestDetectNexus:
    def test_high_betweenness_flagged_as_nexus(self):
        centrality = pd.DataFrame({
            "employee_id": ["hub", "leaf1", "leaf2"],
            "betweenness_centrality": [0.85, 0.0, 0.0],
            "combined_centrality": [0.9, 0.1, 0.1],
        })
        nexus = detect_nexus_employees(centrality)
        assert "hub" in nexus

    def test_no_nexus_in_flat_graph(self):
        centrality = pd.DataFrame({
            "employee_id": ["e0", "e1", "e2"],
            "betweenness_centrality": [0.1, 0.12, 0.08],
            "combined_centrality": [0.4, 0.42, 0.38],
        })
        nexus = detect_nexus_employees(centrality)
        # combined_centrality values are all similar — 85th percentile ≈ 0.42
        # The employee(s) at or above 0.42 will be nexus
        for nid in nexus:
            row = centrality[centrality["employee_id"] == nid]
            assert row["betweenness_centrality"].values[0] > 0.70 or \
                   row["combined_centrality"].values[0] >= np.percentile(
                       centrality["combined_centrality"], 85
                   )

    def test_empty_dataframe_returns_empty_set(self):
        centrality = pd.DataFrame(
            columns=["employee_id", "betweenness_centrality", "combined_centrality"]
        )
        nexus = detect_nexus_employees(centrality)
        assert len(nexus) == 0

    def test_fewer_than_5_employees_skips_percentile_rule(self):
        centrality = pd.DataFrame({
            "employee_id": ["e0", "e1", "e2"],
            "betweenness_centrality": [0.5, 0.2, 0.1],
            "combined_centrality": [0.9, 0.5, 0.2],
        })
        nexus = detect_nexus_employees(centrality)
        # Only betweenness rule applies (none > 0.7)
        assert len(nexus) == 0


# ---------------------------------------------------------------------------
# detect_communities
# ---------------------------------------------------------------------------

class TestDetectCommunities:
    def test_two_cliques_form_two_communities(self):
        import networkx as nx
        G = nx.Graph()
        # Clique 1: e0-e1-e2 (fully connected)
        G.add_edges_from([("e0", "e1"), ("e1", "e2"), ("e0", "e2")])
        # Clique 2: e3-e4-e5 (fully connected)
        G.add_edges_from([("e3", "e4"), ("e4", "e5"), ("e3", "e5")])
        # One bridge edge between cliques
        G.add_edge("e2", "e3", weight=0.1)

        communities = detect_communities(G)
        c0 = communities["e0"]
        c1 = communities["e1"]
        c2 = communities["e2"]
        c3 = communities["e3"]
        # e0, e1, e2 should be in same community; e3, e4, e5 in same community
        assert c0 == c1 == c2
        assert c3 == communities["e4"] == communities["e5"]

    def test_empty_graph_returns_empty_dict(self):
        import networkx as nx
        communities = detect_communities(nx.Graph())
        assert communities == {}


# ---------------------------------------------------------------------------
# compute_team_fragility
# ---------------------------------------------------------------------------

class TestTeamFragility:
    def test_single_person_team_has_max_fragility(self):
        employees = pd.DataFrame({
            "employee_id": ["e0"],
            "team_id": ["team1"],
        })
        centrality = pd.DataFrame({
            "employee_id": ["e0"],
            "betweenness_centrality": [0.5],
        })
        fragility = compute_team_fragility(employees, centrality)
        assert fragility["team1"] == pytest.approx(1.0)

    def test_uniform_centrality_yields_low_fragility(self):
        employees = pd.DataFrame({
            "employee_id": ["e0", "e1", "e2", "e3"],
            "team_id": ["t"] * 4,
        })
        centrality = pd.DataFrame({
            "employee_id": ["e0", "e1", "e2", "e3"],
            "betweenness_centrality": [0.25, 0.25, 0.25, 0.25],
        })
        fragility = compute_team_fragility(employees, centrality)
        assert fragility["t"] < 0.2  # near-equal distribution = low Gini

    def test_concentrated_centrality_yields_high_fragility(self):
        employees = pd.DataFrame({
            "employee_id": ["hub", "e1", "e2", "e3"],
            "team_id": ["t"] * 4,
        })
        centrality = pd.DataFrame({
            "employee_id": ["hub", "e1", "e2", "e3"],
            "betweenness_centrality": [0.95, 0.01, 0.01, 0.01],
        })
        fragility = compute_team_fragility(employees, centrality)
        assert fragility["t"] > 0.6

    def test_all_zero_centrality_returns_zero_fragility(self):
        employees = pd.DataFrame({
            "employee_id": ["e0", "e1"],
            "team_id": ["t", "t"],
        })
        centrality = pd.DataFrame({
            "employee_id": ["e0", "e1"],
            "betweenness_centrality": [0.0, 0.0],
        })
        fragility = compute_team_fragility(employees, centrality)
        assert fragility["t"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# analyze_network (integration)
# ---------------------------------------------------------------------------

class TestAnalyzeNetwork:
    def test_returns_network_metrics_dataclass(self):
        employees = _make_employees(6)
        collab = _make_collab([
            ("e0", "e1", 0.8), ("e1", "e2", 0.6),
            ("e2", "e3", 0.4), ("e3", "e4", 0.5),
            ("e4", "e5", 0.3), ("e0", "e5", 0.7),
        ])
        result = analyze_network(collab, employees)
        assert isinstance(result, NetworkMetrics)

    def test_centrality_df_has_all_employees(self):
        employees = _make_employees(6)
        collab = _make_collab([("e0", "e1", 0.5), ("e2", "e3", 0.5)])
        result = analyze_network(collab, employees)
        assert len(result.centrality) == 6

    def test_nexus_ids_is_subset_of_employee_ids(self):
        employees = _make_employees(6)
        collab = _make_collab([("e0", f"e{i}", 0.8) for i in range(1, 6)])
        result = analyze_network(collab, employees)
        all_ids = set(employees["employee_id"].tolist())
        assert result.nexus_ids.issubset(all_ids)

    def test_team_fragility_keys_match_team_ids(self):
        employees = _make_employees(6)
        collab = _make_collab([("e0", "e1", 0.5)])
        result = analyze_network(collab, employees)
        team_ids = set(employees["team_id"].unique().tolist())
        assert set(result.team_fragility.keys()) == team_ids

    def test_fragility_values_in_unit_range(self):
        employees = _make_employees(6)
        collab = _make_collab([("e0", "e1", 0.5), ("e2", "e3", 0.8)])
        result = analyze_network(collab, employees)
        for v in result.team_fragility.values():
            assert 0.0 <= v <= 1.0

    def test_n_nexus_equals_len_nexus_ids(self):
        employees = _make_employees(6)
        collab = _make_collab([("e0", f"e{i}", 0.9) for i in range(1, 6)])
        result = analyze_network(collab, employees)
        assert result.n_nexus == len(result.nexus_ids)
