"""Plotly-based interactive network graph for the drill-down explorer.

Builds a force-layout scatter plot from a NetworkX graph. Nodes are sized
by impact score and colored by simulation status. Edges are colored by
relationship type and weighted by interaction_weight.
"""

import logging
from typing import Optional

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# Node color palette (BRAND.md compliant)
_STATUS_COLORS: dict[str, str] = {
    "nexus":     "#C8982A",   # gold — organizational nexus
    "protected": "#7C4DBD",   # purple — force-retained
    "retained":  "#27B97C",   # green — suggested retention
    "at_risk":   "#F07020",   # orange — under review (never red)
    "default":   "#6B7280",   # gray — unassigned
}

_REL_COLORS: dict[str, str] = {
    "reports_to":      "rgba(0,51,102,0.4)",
    "collaborates_with": "rgba(107,114,128,0.3)",
    "mentors":         "rgba(200,152,42,0.5)",
}

_NODE_SIZE_MIN = 8
_NODE_SIZE_MAX = 28


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_org_graph(collaboration_df: pd.DataFrame) -> nx.Graph:
    """Build an undirected weighted graph from the collaboration DataFrame.

    Args:
        collaboration_df: DataFrame with source_id, target_id,
                          relationship_type, interaction_weight.

    Returns:
        nx.Graph where edge attributes carry 'weight' and 'relationship_type'.
        When multiple edges exist between the same pair, the one with the
        highest interaction_weight is kept.
    """
    G = nx.Graph()
    if collaboration_df.empty:
        return G

    for _, row in collaboration_df.iterrows():
        src = str(row["source_id"])
        tgt = str(row["target_id"])
        if src == tgt:
            continue
        rel = str(row.get("relationship_type", "collaborates_with"))
        w = float(row.get("interaction_weight", 0.5))

        if G.has_edge(src, tgt):
            if w > G[src][tgt]["weight"]:
                G[src][tgt]["weight"] = w
                G[src][tgt]["relationship_type"] = rel
        else:
            G.add_edge(src, tgt, weight=w, relationship_type=rel)

    return G


def filter_graph_to_scope(
    G: nx.Graph,
    employee_ids: set[str],
    max_nodes: int = 80,
) -> nx.Graph:
    """Return a subgraph restricted to `employee_ids`, capped at max_nodes.

    When the intersection exceeds max_nodes, the top-degree nodes are kept.
    """
    scope = set(G.nodes) & employee_ids
    if len(scope) > max_nodes:
        degrees = {n: G.degree(n) for n in scope}
        scope = set(sorted(scope, key=lambda n: -degrees[n])[:max_nodes])
    return G.subgraph(scope).copy()


# ---------------------------------------------------------------------------
# Plotly figure builder
# ---------------------------------------------------------------------------

def render_network_graph(
    graph: nx.Graph,
    employee_table: pd.DataFrame,
    nexus_ids: set[str] | None = None,
    simulation_status: dict[str, str] | None = None,
    title: str = "Collaboration Network",
    height: int = 560,
    seed: int = 42,
) -> go.Figure:
    """Build a Plotly scatter figure from a NetworkX graph.

    Args:
        graph: NetworkX graph (from build_org_graph / filter_graph_to_scope).
        employee_table: DashboardData.employee_table for name / role lookups.
        nexus_ids: Set of nexus employee IDs.
        simulation_status: employee_id → 'retained' | 'at_risk' | 'protected'.
        title: Figure title string.
        height: Figure height in pixels.
        seed: Layout seed for reproducibility.

    Returns:
        Plotly Figure ready for st.plotly_chart().
    """
    nexus_ids = nexus_ids or set()
    simulation_status = simulation_status or {}

    if len(graph.nodes) == 0:
        return _empty_figure(title, height)

    # Force-directed layout
    pos = nx.spring_layout(graph, seed=seed, k=2.0 / max(len(graph.nodes) ** 0.5, 1))

    # Lookup dictionaries from employee_table
    emp_lookup: dict[str, dict] = {}
    if not employee_table.empty:
        for _, row in employee_table.iterrows():
            eid = str(row["employee_id"])
            emp_lookup[eid] = {
                "name":   str(row.get("full_name", eid)),
                "role":   str(row.get("role_title", "")),
                "impact": float(row.get("impact_score", 50)),
                "cost":   float(row.get("total_cost", 0)),
                "skill":  str(row.get("top_skill", "")),
                "dept":   str(row.get("department", "")),
            }

    # Build edge traces (one per relationship type for legend)
    edge_traces = _build_edge_traces(graph, pos)

    # Build node trace
    node_trace = _build_node_trace(
        graph, pos, emp_lookup, nexus_ids, simulation_status
    )

    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            title=dict(
                text=title,
                font=dict(family="Fraunces, Georgia, serif", size=16, color="#003366"),
                x=0,
                xanchor="left",
            ),
            showlegend=True,
            hovermode="closest",
            height=height,
            margin=dict(l=20, r=20, t=52, b=20),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            paper_bgcolor="#F4F6F9",
            plot_bgcolor="#F4F6F9",
            legend=dict(
                x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#E0EAF4", borderwidth=1,
                font=dict(family="Plus Jakarta Sans, sans-serif", size=10),
            ),
        ),
    )
    return fig


def _build_edge_traces(
    G: nx.Graph,
    pos: dict,
) -> list[go.Scatter]:
    """One trace per relationship type for proper legend grouping."""
    by_rel: dict[str, list[tuple]] = {}
    for u, v, data in G.edges(data=True):
        rel = data.get("relationship_type", "collaborates_with")
        by_rel.setdefault(rel, []).append((u, v, data.get("weight", 0.5)))

    traces = []
    for rel, edges in by_rel.items():
        x_vals, y_vals = [], []
        widths = []
        for u, v, w in edges:
            if u in pos and v in pos:
                x_vals += [pos[u][0], pos[v][0], None]
                y_vals += [pos[u][1], pos[v][1], None]
                widths.append(w)
        avg_w = sum(widths) / max(len(widths), 1)
        traces.append(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines",
            line=dict(width=1 + avg_w * 2, color=_REL_COLORS.get(rel, "rgba(150,150,150,0.3)")),
            hoverinfo="none",
            name=rel.replace("_", " ").title(),
            legendgroup=rel,
            showlegend=True,
        ))
    return traces


def _build_node_trace(
    G: nx.Graph,
    pos: dict,
    emp_lookup: dict[str, dict],
    nexus_ids: set[str],
    simulation_status: dict[str, str],
) -> go.Scatter:
    x_vals, y_vals = [], []
    colors, sizes, texts, customdata = [], [], [], []

    for node in G.nodes:
        if node not in pos:
            continue
        x_vals.append(pos[node][0])
        y_vals.append(pos[node][1])

        info = emp_lookup.get(node, {})
        impact = info.get("impact", 50)
        name = info.get("name", node[:8])
        role = info.get("role", "")
        cost = info.get("cost", 0)
        skill = info.get("skill", "")
        dept = info.get("dept", "")
        degree = G.degree(node)

        # Color priority: nexus > protected > retained/at_risk > default
        if node in nexus_ids:
            color = _STATUS_COLORS["nexus"]
        else:
            status = simulation_status.get(node, "default")
            color = _STATUS_COLORS.get(status, _STATUS_COLORS["default"])
        colors.append(color)

        # Node size proportional to impact [8, 28]
        size = _NODE_SIZE_MIN + (impact / 100) * (_NODE_SIZE_MAX - _NODE_SIZE_MIN)
        sizes.append(round(size, 1))

        texts.append(name.split()[0] if name else node[:6])  # first name label
        customdata.append((
            f"<b>{name}</b><br>"
            f"{role}<br>"
            f"<span style='color:#C8982A'>Impact: {impact:.0f}</span><br>"
            f"Dept: {dept}<br>"
            f"Top skill: {skill}<br>"
            f"Cost: ${cost:,.0f}<br>"
            f"Connections: {degree}"
        ))

    return go.Scatter(
        x=x_vals,
        y=y_vals,
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=1.5, color="#ffffff"),
            opacity=0.92,
        ),
        text=texts,
        textposition="top center",
        textfont=dict(family="Plus Jakarta Sans, sans-serif", size=8, color="#374151"),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=customdata,
        name="Employees",
        showlegend=False,
    )


def _empty_figure(title: str, height: int) -> go.Figure:
    return go.Figure(
        layout=go.Layout(
            title=dict(text=title, font=dict(size=16, color="#003366")),
            height=height,
            annotations=[dict(
                text="No graph data available for the current selection.",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False,
                font=dict(family="Plus Jakarta Sans, sans-serif", size=13, color="#6B7280"),
            )],
            paper_bgcolor="#F4F6F9",
            plot_bgcolor="#F4F6F9",
        )
    )


# ---------------------------------------------------------------------------
# Legend helper
# ---------------------------------------------------------------------------

def status_legend_html() -> str:
    """Return HTML for a compact node-status legend."""
    items = [
        (_STATUS_COLORS["nexus"],     "Organizational Nexus"),
        (_STATUS_COLORS["protected"], "Force Retained"),
        (_STATUS_COLORS["retained"],  "Suggested Retention"),
        (_STATUS_COLORS["at_risk"],   "Under Review"),
        (_STATUS_COLORS["default"],   "Unassigned"),
    ]
    dots = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:16px;">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:{c};'
        f'flex-shrink:0;"></span>'
        f'<span style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:10px;'
        f'color:#374151;">{lbl}</span></span>'
        for c, lbl in items
    )
    return f'<div style="padding:8px 0;">{dots}</div>'
