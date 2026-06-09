"""NetworkX collaboration graph analysis: centrality, nexus detection, community detection."""

import logging
from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_NEXUS_BETWEENNESS_THRESHOLD = 0.70
_NEXUS_COMBINED_PERCENTILE = 85
_LARGE_GRAPH_THRESHOLD = 1_000  # use faster algorithm above this node count


@dataclass
class NetworkMetrics:
    """Per-employee centrality metrics and graph-level statistics."""

    centrality: pd.DataFrame  # columns: employee_id, degree_centrality, betweenness_centrality, eigenvector_centrality, pagerank, combined_centrality
    nexus_ids: set[str]
    communities: dict[str, int]  # employee_id → community_id (0-indexed)
    team_fragility: dict[str, float]  # team_id → Gini-based fragility [0, 1]
    graph_density: float
    n_components: int
    n_nexus: int = field(init=False)

    def __post_init__(self) -> None:
        self.n_nexus = len(self.nexus_ids)


def build_graph(collaboration_df: pd.DataFrame) -> nx.Graph:
    """Build undirected weighted graph from collaboration edges.

    When source and target appear in multiple rows, the maximum weight edge is kept.
    """
    G: nx.Graph = nx.Graph()
    for _, row in collaboration_df.iterrows():
        src = str(row["source_id"])
        tgt = str(row["target_id"])
        w = float(row["interaction_weight"])
        if G.has_edge(src, tgt):
            G[src][tgt]["weight"] = max(G[src][tgt]["weight"], w)
        else:
            G.add_edge(src, tgt, weight=w)
    return G


def compute_centrality_metrics(
    G: nx.Graph,
    employees_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute degree, betweenness, eigenvector, and PageRank centrality.

    Employees with no collaboration edges are added as isolated nodes so every
    employee receives a metric row (value = 0.0).
    """
    emp_ids = [str(eid) for eid in employees_df["employee_id"].tolist()]

    for eid in emp_ids:
        if eid not in G:
            G.add_node(eid)

    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True)

    try:
        eigenvector = nx.eigenvector_centrality(
            G, weight="weight", max_iter=500, tol=1e-6
        )
    except nx.PowerIterationFailedConvergence:
        logger.warning(
            "Eigenvector centrality did not converge for graph with %d nodes; using degree as fallback",
            G.number_of_nodes(),
        )
        eigenvector = degree

    pagerank = nx.pagerank(G, weight="weight", max_iter=200)

    rows = [
        {
            "employee_id": eid,
            "degree_centrality": round(degree.get(eid, 0.0), 4),
            "betweenness_centrality": round(betweenness.get(eid, 0.0), 4),
            "eigenvector_centrality": round(eigenvector.get(eid, 0.0), 4),
            "pagerank": round(pagerank.get(eid, 0.0), 4),
        }
        for eid in emp_ids
    ]

    df = pd.DataFrame(rows)

    # Normalize each metric to [0, 1] then average → combined_centrality
    for col in [
        "degree_centrality",
        "betweenness_centrality",
        "eigenvector_centrality",
        "pagerank",
    ]:
        max_val = df[col].max()
        df[f"_{col}_norm"] = df[col] / max_val if max_val > 0 else 0.0

    df["combined_centrality"] = (
        df[["_degree_centrality_norm", "_betweenness_centrality_norm",
            "_eigenvector_centrality_norm", "_pagerank_norm"]]
        .mean(axis=1)
        .round(4)
    )

    df.drop(columns=[c for c in df.columns if c.startswith("_")], inplace=True)
    return df


def detect_nexus_employees(centrality_df: pd.DataFrame) -> set[str]:
    """Return employee IDs classified as nexus.

    Criteria: betweenness > 0.70 OR combined_centrality ≥ 85th percentile.
    Requires at least 5 employees to apply the percentile rule.
    """
    nexus: set[str] = set()

    high_bw = centrality_df[
        centrality_df["betweenness_centrality"] > _NEXUS_BETWEENNESS_THRESHOLD
    ]["employee_id"]
    nexus.update(high_bw.tolist())

    if len(centrality_df) >= 5:
        p85 = float(
            np.percentile(centrality_df["combined_centrality"], _NEXUS_COMBINED_PERCENTILE)
        )
        if p85 > 0:
            high_combined = centrality_df[
                centrality_df["combined_centrality"] >= p85
            ]["employee_id"]
            nexus.update(high_combined.tolist())

    return nexus


def detect_communities(G: nx.Graph) -> dict[str, int]:
    """Detect natural clusters using greedy modularity (small graphs) or label propagation (large).

    Returns empty dict if graph has no nodes.
    """
    if G.number_of_nodes() == 0:
        return {}

    if G.number_of_nodes() >= _LARGE_GRAPH_THRESHOLD:
        # label_propagation is O(n + m), safe for large graphs
        raw = nx.community.label_propagation_communities(G)
    else:
        raw = nx.community.greedy_modularity_communities(G)

    community_map: dict[str, int] = {}
    for idx, community in enumerate(raw):
        for node in community:
            community_map[str(node)] = idx

    logger.debug("Community detection: %d communities", len(set(community_map.values())))
    return community_map


def compute_team_fragility(
    employees_df: pd.DataFrame,
    centrality_df: pd.DataFrame,
) -> dict[str, float]:
    """Compute team fragility as the Gini coefficient of betweenness centrality within the team.

    High fragility (close to 1.0) means one or two individuals concentrate the team's connectivity.
    Single-person teams always return 1.0.
    """
    centrality_map = dict(
        zip(centrality_df["employee_id"], centrality_df["betweenness_centrality"], strict=False)
    )

    fragility: dict[str, float] = {}
    for team_id, group in employees_df.groupby("team_id"):
        scores = np.array(
            [centrality_map.get(str(eid), 0.0) for eid in group["employee_id"]]
        )
        n = len(scores)
        if n < 2:
            fragility[str(team_id)] = 1.0
            continue
        if scores.sum() == 0.0:
            fragility[str(team_id)] = 0.0
            continue
        arr = np.sort(scores)
        gini = float(
            (2 * np.dot(np.arange(1, n + 1), arr)) / (n * arr.sum()) - (n + 1) / n
        )
        fragility[str(team_id)] = round(float(np.clip(gini, 0.0, 1.0)), 4)

    return fragility


def analyze_network(
    collaboration_df: pd.DataFrame,
    employees_df: pd.DataFrame,
) -> NetworkMetrics:
    """Full network analysis pipeline: build graph → centrality → nexus → communities → fragility."""
    G = build_graph(collaboration_df)
    centrality_df = compute_centrality_metrics(G, employees_df)
    nexus_ids = detect_nexus_employees(centrality_df)
    communities = detect_communities(G)
    team_fragility = compute_team_fragility(employees_df, centrality_df)

    n_components = nx.number_connected_components(G) if G.number_of_nodes() > 0 else 0
    density = round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0.0

    logger.info(
        "Network: %d nodes | %d edges | density=%.3f | nexus=%d | communities=%d",
        G.number_of_nodes(),
        G.number_of_edges(),
        density,
        len(nexus_ids),
        len(set(communities.values())),
    )

    return NetworkMetrics(
        centrality=centrality_df,
        nexus_ids=nexus_ids,
        communities=communities,
        team_fragility=team_fragility,
        graph_density=density,
        n_components=n_components,
    )
