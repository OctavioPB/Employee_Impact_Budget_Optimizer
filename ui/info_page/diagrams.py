"""Interactive Plotly diagrams for the Info page."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


_COLORS = {
    "primary": "#003366",
    "gold": "#C8982A",
    "gold_light": "#E8C46A",
    "light": "#F4F6F9",
    "green": "#27B97C",
    "purple": "#7C4DBD",
    "orange": "#F07020",
}


def _base_layout(title: str = "") -> dict:
    return dict(
        title=title,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#374151"),
        margin=dict(l=20, r=20, t=40, b=20),
    )


# ---------------------------------------------------------------------------
# Medallion Architecture diagram
# ---------------------------------------------------------------------------

def medallion_architecture_diagram() -> go.Figure:
    """Interactive Medallion Architecture flow diagram."""
    fig = go.Figure()

    layers = [
        ("DATA SOURCES",  0.5, 5.5, "#E0EAF4", "#003366", "ERP / HRIS / CSV / Excel"),
        ("BRONZE LAYER",  0.5, 4.0, "#FEF0E6", "#7A3800", "Raw ingestion · No transformation"),
        ("SILVER LAYER",  0.5, 2.5, "#E0F7EF", "#0D5C3A", "Cleansed · Normalised · Validated"),
        ("GOLD LAYER",    0.5, 1.0, "#F0EBF9", "#3D1F70", "Aggregated · Dashboard-ready"),
    ]

    for name, x, y, bg, txt, sub in layers:
        fig.add_shape(
            type="rect", x0=x, y0=y - 0.55, x1=x + 9, y1=y + 0.55,
            fillcolor=bg, line=dict(color=txt, width=1.5), layer="below",
        )
        fig.add_annotation(
            x=x + 4.5, y=y + 0.2, text=f"<b>{name}</b>",
            showarrow=False,
            font=dict(size=11, color=txt, family="Plus Jakarta Sans"),
        )
        fig.add_annotation(
            x=x + 4.5, y=y - 0.2, text=sub,
            showarrow=False,
            font=dict(size=9, color=txt, family="Plus Jakarta Sans"),
        )

    # Arrows between layers
    for y_start, y_end in [(4.0, 3.55), (2.5, 2.05), (1.0, 0.55)]:
        fig.add_annotation(
            x=5, y=y_end, ax=5, ay=y_start,
            arrowhead=2, arrowsize=1.2, arrowwidth=2,
            arrowcolor=_COLORS["gold"],
            showarrow=True, text="",
        )

    # UI consumers
    consumers = ["Executive\nDashboard", "Simulation\nEngine", "ML Models", "Audit\nTrail"]
    x_positions = [1.5, 3.5, 6.0, 8.0]
    for label, xpos in zip(consumers, x_positions):
        fig.add_shape(
            type="rect", x0=xpos - 0.8, y0=-0.9, x1=xpos + 0.8, y1=-0.1,
            fillcolor="#003366", line=dict(color="#E8C46A", width=1),
        )
        fig.add_annotation(
            x=xpos, y=-0.5, text=label,
            showarrow=False,
            font=dict(size=8, color="white", family="Plus Jakarta Sans"),
        )
        fig.add_annotation(
            x=xpos, y=0.45, ax=xpos, ay=-0.1,
            arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor=_COLORS["gold_light"],
            showarrow=True, text="",
        )

    fig.add_annotation(
        x=5, y=-1.1,
        text="UI CONSUMERS",
        showarrow=False,
        font=dict(size=8, color="#6B7280", family="Plus Jakarta Sans"),
    )

    fig.update_layout(
        **_base_layout("Medallion Data Architecture"),
        xaxis=dict(visible=False, range=[0, 10]),
        yaxis=dict(visible=False, range=[-1.3, 6.3]),
        height=420,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Impact Score breakdown (Business view)
# ---------------------------------------------------------------------------

def impact_score_breakdown_chart() -> go.Figure:
    """Donut chart explaining Impact Score composition."""
    labels = ["KPI History & Trend", "Collaboration Centrality",
              "Skill Criticality", "Replacement Cost"]
    values = [40, 30, 20, 10]
    colors = [_COLORS["primary"], _COLORS["green"], _COLORS["purple"], _COLORS["orange"]]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.60,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(family="Plus Jakarta Sans", size=11),
        hovertemplate="<b>%{label}</b><br>Weight: %{value}%<extra></extra>",
    ))
    fig.add_annotation(
        text="<b>Impact</b><br>Score",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, family="Fraunces, serif", color="#003366"),
    )
    fig.update_layout(
        **_base_layout("Impact Score Components"),
        height=320,
        showlegend=True,
        legend=dict(font=dict(family="Plus Jakarta Sans", size=10)),
    )
    return fig


# ---------------------------------------------------------------------------
# Network graph example (nexus employees)
# ---------------------------------------------------------------------------

def collaboration_network_example() -> go.Figure:
    """Small example network showing nexus employee concept."""
    np.random.seed(42)
    n_nodes = 18
    angles = np.linspace(0, 2 * np.pi, n_nodes, endpoint=False)
    x_ring = np.cos(angles) * 2
    y_ring = np.sin(angles) * 2

    # Nexus node at center
    x_all = np.append([0.0], x_ring)
    y_all = np.append([0.0], y_ring)
    labels = ["Nexus Employee"] + [f"Team Member {i}" for i in range(n_nodes)]
    colors = ["#C8982A"] + ["#003366"] * 6 + ["#27B97C"] * 6 + ["#7C4DBD"] * 6
    sizes = [28] + [14] * n_nodes

    edge_x, edge_y = [], []
    # Nexus connects to all
    for i in range(1, n_nodes + 1):
        edge_x += [0, x_all[i], None]
        edge_y += [0, y_all[i], None]
    # Some ring connections
    for i in range(1, n_nodes + 1):
        j = (i % n_nodes) + 1
        edge_x += [x_all[i], x_all[j], None]
        edge_y += [y_all[i], y_all[j], None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#E0EAF4", width=1),
        hoverinfo="none", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=x_all, y=y_all, mode="markers+text",
        marker=dict(color=colors, size=sizes, line=dict(color="white", width=2)),
        text=["<b>NEXUS</b>"] + ["" for _ in range(n_nodes)],
        textfont=dict(size=9, color="white"),
        textposition="middle center",
        hovertext=labels,
        hovertemplate="<b>%{hovertext}</b><extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        **_base_layout("Collaboration Network — Nexus Employee"),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=300,
    )
    return fig


# ---------------------------------------------------------------------------
# Human-in-the-loop decision flow
# ---------------------------------------------------------------------------

def decision_flow_diagram() -> go.Figure:
    """Flowchart: model → human review → final decision."""
    fig = go.Figure()

    nodes = [
        ("Data & Context", 1, 4, "#E0EAF4", "#003366"),
        ("EIBO Analysis", 3, 4, "#003366", "white"),
        ("Suggestions", 5, 4, "#F0EBF9", "#3D1F70"),
        ("Human Review", 7, 4, "#FEF0E6", "#7A3800"),
        ("Final Decision", 9, 4, "#E0F7EF", "#0D5C3A"),
        ("Override &\nAnnotate", 7, 2, "#003366", "white"),
    ]
    for label, x, y, bg, txt in nodes:
        fig.add_shape(
            type="rect", x0=x - 0.85, y0=y - 0.55, x1=x + 0.85, y1=y + 0.55,
            fillcolor=bg, line=dict(color=txt if bg != "#003366" else "#E8C46A", width=1.5),
        )
        fig.add_annotation(
            x=x, y=y, text=label, showarrow=False,
            font=dict(size=9, color=txt, family="Plus Jakarta Sans"),
            align="center",
        )

    # Arrows main flow
    for x_start, x_end in [(1.85, 2.15), (3.85, 4.15), (5.85, 6.15), (7.85, 8.15)]:
        fig.add_annotation(
            x=x_end, y=4, ax=x_start, ay=4,
            arrowhead=2, arrowsize=1, arrowwidth=2,
            arrowcolor=_COLORS["gold"], showarrow=True, text="",
        )
    # Override arrow
    fig.add_annotation(
        x=7, y=2.55, ax=7, ay=3.45,
        arrowhead=2, arrowsize=1, arrowwidth=1.5,
        arrowcolor="#E8C46A", showarrow=True, text="",
    )
    fig.add_annotation(
        x=5, y=3, text="Override possible\nat any step",
        showarrow=False, font=dict(size=8, color="#6B7280", family="Plus Jakarta Sans"),
    )

    fig.update_layout(
        **_base_layout("Human-in-the-Loop Decision Process"),
        xaxis=dict(visible=False, range=[0, 10.5]),
        yaxis=dict(visible=False, range=[1, 5]),
        height=280,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# ILP constraint visualization (Engineering view)
# ---------------------------------------------------------------------------

def ilp_feasible_region_chart() -> go.Figure:
    """Visualize the ILP optimization concept with budget vs impact frontier."""
    np.random.seed(42)
    n = 80
    budgets = np.random.uniform(300_000, 1_200_000, n)
    impacts = 0.00005 * budgets + np.random.normal(0, 8, n)
    impacts = np.clip(impacts, 20, 75)

    pareto_budget = np.array([300_000, 450_000, 600_000, 750_000, 900_000, 1_050_000, 1_200_000])
    pareto_impact = np.array([28, 38, 49, 57, 63, 68, 72])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=budgets / 1_000, y=impacts,
        mode="markers",
        marker=dict(color=_COLORS["primary"], size=6, opacity=0.5),
        name="Feasible Solutions",
        hovertemplate="Budget: $%{x:.0f}K<br>Impact: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=pareto_budget / 1_000, y=pareto_impact,
        mode="lines+markers",
        line=dict(color=_COLORS["gold"], width=2.5),
        marker=dict(color=_COLORS["gold"], size=9),
        name="Pareto Frontier",
        hovertemplate="Optimal — Budget: $%{x:.0f}K<br>Impact: %{y:.1f}<extra></extra>",
    ))
    fig.add_vline(
        x=700, line_dash="dash", line_color=_COLORS["orange"],
        annotation_text="Budget Target", annotation_position="top right",
        annotation_font=dict(size=9, color=_COLORS["orange"]),
    )

    fig.update_layout(
        **_base_layout("Multi-Objective Optimization: Budget vs Retained Impact"),
        xaxis=dict(title="Available Budget ($K)", gridcolor="#f0f0f0"),
        yaxis=dict(title="Retained Impact Score (sum)", gridcolor="#f0f0f0"),
        height=340,
        legend=dict(font=dict(family="Plus Jakarta Sans", size=10)),
    )
    return fig


# ---------------------------------------------------------------------------
# Performance trend chart (Business view — use case)
# ---------------------------------------------------------------------------

def sample_performance_trend() -> go.Figure:
    """Sample quarterly KPI trend by department."""
    periods = [f"Q{q} {y}" for y in [2022, 2023, 2024] for q in [1, 2, 3, 4]]
    engineering = [3.4, 3.5, 3.3, 3.6, 3.7, 3.6, 3.8, 3.9, 4.0, 3.9, 4.1, 4.2]
    sales       = [3.0, 3.2, 3.1, 3.5, 3.4, 3.3, 3.6, 3.8, 3.7, 3.9, 3.8, 4.0]
    operations  = [3.2, 3.1, 3.3, 3.2, 3.4, 3.3, 3.2, 3.5, 3.4, 3.6, 3.5, 3.7]

    fig = go.Figure()
    for dept, vals, color in [
        ("Engineering", engineering, _COLORS["primary"]),
        ("Sales", sales, _COLORS["green"]),
        ("Operations", operations, _COLORS["purple"]),
    ]:
        fig.add_trace(go.Scatter(
            x=periods, y=vals, mode="lines+markers",
            name=dept, line=dict(color=color, width=2),
            marker=dict(size=6),
            hovertemplate=f"{dept}<br>%{{x}}: %{{y:.2f}}<extra></extra>",
        ))

    fig.update_layout(
        **_base_layout("Quarterly KPI Trends by Department"),
        xaxis=dict(gridcolor="#f0f0f0", tickangle=-30),
        yaxis=dict(title="Average KPI Score", range=[2.5, 4.5], gridcolor="#f0f0f0"),
        height=320,
        legend=dict(font=dict(family="Plus Jakarta Sans", size=10)),
    )
    return fig


# ---------------------------------------------------------------------------
# Attrition risk heatmap (Business view — concepts)
# ---------------------------------------------------------------------------

def attrition_risk_heatmap() -> go.Figure:
    """Sample attrition risk × impact quadrant chart."""
    np.random.seed(7)
    n = 50
    impact = np.random.uniform(20, 90, n)
    attrition_risk = np.random.uniform(5, 95, n)
    names = [f"Employee {i:02d}" for i in range(n)]

    colors = []
    for imp, risk in zip(impact, attrition_risk):
        if imp > 60 and risk > 60:
            colors.append(_COLORS["orange"])   # High impact, high risk → critical
        elif imp > 60:
            colors.append(_COLORS["green"])    # High impact, low risk → safe
        elif risk > 60:
            colors.append(_COLORS["purple"])   # Low impact, high risk → monitor
        else:
            colors.append(_COLORS["primary"])  # Low impact, low risk → stable

    fig = go.Figure(go.Scatter(
        x=impact, y=attrition_risk,
        mode="markers",
        marker=dict(color=colors, size=10, opacity=0.8, line=dict(color="white", width=1)),
        text=names,
        hovertemplate="<b>%{text}</b><br>Impact Score: %{x:.0f}<br>Attrition Risk: %{y:.0f}%<extra></extra>",
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#E0EAF4")
    fig.add_vline(x=60, line_dash="dash", line_color="#E0EAF4")

    for label, x, y in [
        ("Critical — Intervene Now", 75, 80),
        ("Stable — Key Talent", 75, 20),
        ("Monitor — Flight Risk", 35, 80),
        ("Stable — Standard", 35, 20),
    ]:
        fig.add_annotation(
            x=x, y=y, text=label, showarrow=False,
            font=dict(size=8, color="#6B7280", family="Plus Jakarta Sans"),
        )

    fig.update_layout(
        **_base_layout("Talent Risk Matrix: Impact vs Attrition Risk"),
        xaxis=dict(title="Impact Score", range=[0, 100], gridcolor="#f0f0f0"),
        yaxis=dict(title="Attrition Risk (%)", range=[0, 100], gridcolor="#f0f0f0"),
        height=340,
    )
    return fig
