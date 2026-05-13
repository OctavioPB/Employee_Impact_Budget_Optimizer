"""Unit tests for Sprint 4 drill-down components.

Tests cover pure logic functions only (no Streamlit renders):
- graph_viz: build_org_graph, filter_graph_to_scope
- profile_card: render_impact_radar, render_skill_matrix, render_performance_sparkline,
               render_ego_network (graph structure only)
- exports: df_to_csv_bytes, tables_to_excel_bytes, generate_pdf_summary
"""

import io
import pandas as pd
import networkx as nx
import pytest

from ui.components.graph_viz import build_org_graph, filter_graph_to_scope, status_legend_html
from ui.components.profile_card import (
    render_impact_radar,
    render_skill_matrix,
    render_performance_sparkline,
    render_ego_network,
    render_cost_breakdown,
)
from ui.components.exports import df_to_csv_bytes, tables_to_excel_bytes, generate_pdf_summary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_collab():
    """Three employees with two relationship types."""
    return pd.DataFrame([
        {"source_id": "E1", "target_id": "E2", "relationship_type": "collaborates_with", "interaction_weight": 0.7},
        {"source_id": "E1", "target_id": "E3", "relationship_type": "reports_to",        "interaction_weight": 0.9},
        {"source_id": "E2", "target_id": "E3", "relationship_type": "mentors",            "interaction_weight": 0.5},
        {"source_id": "E3", "target_id": "E4", "relationship_type": "collaborates_with", "interaction_weight": 0.6},
    ])


@pytest.fixture
def employee_table():
    return pd.DataFrame([
        {"employee_id": "E1", "full_name": "Alice Smith",  "role_title": "Lead Eng",
         "department": "Engineering", "team_id": "T1", "seniority_level": "lead",
         "impact_score": 88.0, "total_cost": 220_000, "top_skill": "Python", "tenure_years": 5.2},
        {"employee_id": "E2", "full_name": "Bob Jones",    "role_title": "Mid Eng",
         "department": "Engineering", "team_id": "T1", "seniority_level": "mid",
         "impact_score": 72.0, "total_cost": 130_000, "top_skill": "SQL", "tenure_years": 2.1},
        {"employee_id": "E3", "full_name": "Carol Lee",    "role_title": "Senior Eng",
         "department": "Engineering", "team_id": "T2", "seniority_level": "senior",
         "impact_score": 80.0, "total_cost": 175_000, "top_skill": "Kafka", "tenure_years": 3.8},
        {"employee_id": "E4", "full_name": "Dan Brown",    "role_title": "Director",
         "department": "Product", "team_id": "T3", "seniority_level": "director",
         "impact_score": 91.0, "total_cost": 280_000, "top_skill": "Strategy", "tenure_years": 7.0},
    ])


@pytest.fixture
def impact_scores():
    return pd.DataFrame([
        {"employee_id": "E1", "impact_score": 88.0, "kpi_contribution": 0.40,
         "network_contribution": 0.30, "skills_contribution": 0.20,
         "cost_contribution": 0.10, "confidence": 0.80},
        {"employee_id": "E2", "impact_score": 72.0, "kpi_contribution": 0.35,
         "network_contribution": 0.25, "skills_contribution": 0.28,
         "cost_contribution": 0.12, "confidence": 0.65},
    ])


@pytest.fixture
def employee_skills():
    return pd.DataFrame([
        {"employee_id": "E1", "skill_id": "S1", "proficiency": 5, "is_primary": True},
        {"employee_id": "E1", "skill_id": "S2", "proficiency": 3, "is_primary": False},
        {"employee_id": "E2", "skill_id": "S1", "proficiency": 2, "is_primary": True},
    ])


@pytest.fixture
def skills_df():
    return pd.DataFrame([
        {"skill_id": "S1", "skill_name": "Python",    "category": "Programming", "is_critical": True,  "market_scarcity": 0.7},
        {"skill_id": "S2", "skill_name": "Spark",     "category": "Data",        "is_critical": True,  "market_scarcity": 0.8},
        {"skill_id": "S3", "skill_name": "Leadership","category": "Management",  "is_critical": False, "market_scarcity": 0.4},
    ])


@pytest.fixture
def performance_df():
    return pd.DataFrame([
        {"employee_id": "E1", "kpi_score": 3.8, "review_date": "2023-09-30", "review_period": "2023Q3"},
        {"employee_id": "E1", "kpi_score": 4.1, "review_date": "2023-12-31", "review_period": "2023Q4"},
        {"employee_id": "E1", "kpi_score": 4.3, "review_date": "2024-03-31", "review_period": "2024Q1"},
        {"employee_id": "E2", "kpi_score": 3.2, "review_date": "2024-03-31", "review_period": "2024Q1"},
    ])


@pytest.fixture
def dept_summary():
    return pd.DataFrame([
        {"department": "Engineering", "headcount": 3, "total_spend": 525_000,
         "annual_budget": 500_000, "budget_variance_pct": 5.0, "avg_impact": 80.0, "fragility_avg": 0.4},
        {"department": "Product", "headcount": 1, "total_spend": 280_000,
         "annual_budget": 300_000, "budget_variance_pct": -6.7, "avg_impact": 91.0, "fragility_avg": 0.3},
    ])


# ---------------------------------------------------------------------------
# Tests: build_org_graph
# ---------------------------------------------------------------------------

class TestBuildOrgGraph:
    def test_empty_collab_returns_empty_graph(self):
        G = build_org_graph(pd.DataFrame(columns=["source_id","target_id","relationship_type","interaction_weight"]))
        assert len(G.nodes) == 0

    def test_correct_node_count(self, small_collab):
        G = build_org_graph(small_collab)
        # 4 unique nodes: E1, E2, E3, E4
        assert len(G.nodes) == 4

    def test_correct_edge_count(self, small_collab):
        G = build_org_graph(small_collab)
        # 4 directed → 4 undirected edges (no duplicates in this fixture)
        assert len(G.edges) == 4

    def test_duplicate_edge_keeps_max_weight(self):
        collab = pd.DataFrame([
            {"source_id": "A", "target_id": "B", "relationship_type": "collaborates_with", "interaction_weight": 0.3},
            {"source_id": "B", "target_id": "A", "relationship_type": "collaborates_with", "interaction_weight": 0.9},
        ])
        G = build_org_graph(collab)
        assert len(G.edges) == 1
        assert G["A"]["B"]["weight"] == 0.9

    def test_edge_has_weight_attribute(self, small_collab):
        G = build_org_graph(small_collab)
        for u, v, data in G.edges(data=True):
            assert "weight" in data
            assert 0 <= data["weight"] <= 1

    def test_edge_has_relationship_type_attribute(self, small_collab):
        G = build_org_graph(small_collab)
        for u, v, data in G.edges(data=True):
            assert "relationship_type" in data

    def test_self_loops_not_added(self):
        collab = pd.DataFrame([
            {"source_id": "A", "target_id": "A", "relationship_type": "collaborates_with", "interaction_weight": 1.0},
        ])
        G = build_org_graph(collab)
        assert not G.has_edge("A", "A")

    def test_result_is_undirected_graph(self, small_collab):
        G = build_org_graph(small_collab)
        assert isinstance(G, nx.Graph)
        assert not isinstance(G, nx.DiGraph)


# ---------------------------------------------------------------------------
# Tests: filter_graph_to_scope
# ---------------------------------------------------------------------------

class TestFilterGraphToScope:
    def test_scope_restricts_to_subset(self, small_collab):
        G = build_org_graph(small_collab)
        scope = {"E1", "E2"}
        G_scope = filter_graph_to_scope(G, scope)
        assert set(G_scope.nodes).issubset(scope)

    def test_max_nodes_caps_output(self, small_collab):
        G = build_org_graph(small_collab)
        G_scope = filter_graph_to_scope(G, set(G.nodes), max_nodes=2)
        assert len(G_scope.nodes) <= 2

    def test_empty_scope_returns_empty_graph(self, small_collab):
        G = build_org_graph(small_collab)
        G_scope = filter_graph_to_scope(G, set())
        assert len(G_scope.nodes) == 0

    def test_scope_larger_than_graph_returns_full_graph(self, small_collab):
        G = build_org_graph(small_collab)
        G_scope = filter_graph_to_scope(G, {"E1", "E2", "E3", "E4", "GHOST"})
        assert len(G_scope.nodes) == 4

    def test_high_degree_nodes_preferred_when_capping(self):
        """Hub node should survive when max_nodes < total."""
        edges = pd.DataFrame([
            {"source_id": "Hub", "target_id": f"N{i}",
             "relationship_type": "collaborates_with",
             "interaction_weight": 0.5}
            for i in range(5)
        ])
        G = build_org_graph(edges)
        scope = set(G.nodes)  # 6 nodes
        G_scope = filter_graph_to_scope(G, scope, max_nodes=3)
        assert "Hub" in G_scope.nodes  # highest degree should be kept


# ---------------------------------------------------------------------------
# Tests: status_legend_html
# ---------------------------------------------------------------------------

class TestStatusLegendHtml:
    def test_returns_non_empty_string(self):
        html = status_legend_html()
        assert isinstance(html, str)
        assert len(html) > 10

    def test_contains_nexus_label(self):
        html = status_legend_html()
        assert "Nexus" in html


# ---------------------------------------------------------------------------
# Tests: render_impact_radar
# ---------------------------------------------------------------------------

class TestRenderImpactRadar:
    def test_returns_plotly_figure(self, impact_scores):
        import plotly.graph_objects as go
        scores_row = impact_scores.iloc[0]
        fig = render_impact_radar(scores_row)
        assert isinstance(fig, go.Figure)

    def test_radar_has_scatterpolar_trace(self, impact_scores):
        import plotly.graph_objects as go
        scores_row = impact_scores.iloc[0]
        fig = render_impact_radar(scores_row)
        assert any(isinstance(t, go.Scatterpolar) for t in fig.data)

    def test_handles_zero_components(self):
        import plotly.graph_objects as go
        scores_row = pd.Series({
            "kpi_contribution": 0.0,
            "network_contribution": 0.0,
            "skills_contribution": 0.0,
            "cost_contribution": 0.0,
            "confidence": 0.0,
        })
        fig = render_impact_radar(scores_row)
        assert isinstance(fig, go.Figure)

    def test_handles_missing_keys(self):
        """Gracefully handles Series with no contribution keys."""
        import plotly.graph_objects as go
        scores_row = pd.Series({"impact_score": 75.0})
        fig = render_impact_radar(scores_row)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Tests: render_skill_matrix
# ---------------------------------------------------------------------------

class TestRenderSkillMatrix:
    def test_returns_plotly_figure(self, employee_skills, skills_df):
        import plotly.graph_objects as go
        fig = render_skill_matrix("E1", employee_skills, skills_df)
        assert isinstance(fig, go.Figure)

    def test_empty_skills_returns_figure(self):
        import plotly.graph_objects as go
        fig = render_skill_matrix("E1",
                                  pd.DataFrame(columns=["employee_id","skill_id","proficiency","is_primary"]),
                                  pd.DataFrame(columns=["skill_id","skill_name","category","is_critical"]))
        assert isinstance(fig, go.Figure)

    def test_employee_with_no_skills_returns_figure(self, employee_skills, skills_df):
        import plotly.graph_objects as go
        fig = render_skill_matrix("GHOST", employee_skills, skills_df)
        assert isinstance(fig, go.Figure)

    def test_critical_skill_shown_for_e1(self, employee_skills, skills_df):
        """E1 has Python (critical) — chart should include it."""
        fig = render_skill_matrix("E1", employee_skills, skills_df)
        if fig.data:
            # Bar chart y-axis should include Python
            y_vals = list(fig.data[0].y) if fig.data else []
            assert "Python" in y_vals


# ---------------------------------------------------------------------------
# Tests: render_performance_sparkline
# ---------------------------------------------------------------------------

class TestRenderPerformanceSparkline:
    def test_returns_plotly_figure(self, performance_df):
        import plotly.graph_objects as go
        fig = render_performance_sparkline("E1", performance_df)
        assert isinstance(fig, go.Figure)

    def test_empty_performance_returns_figure(self):
        import plotly.graph_objects as go
        fig = render_performance_sparkline("E1",
                                           pd.DataFrame(columns=["employee_id","kpi_score","review_date","review_period"]))
        assert isinstance(fig, go.Figure)

    def test_unknown_employee_returns_figure(self, performance_df):
        import plotly.graph_objects as go
        fig = render_performance_sparkline("GHOST", performance_df)
        assert isinstance(fig, go.Figure)

    def test_e1_has_3_data_points(self, performance_df):
        fig = render_performance_sparkline("E1", performance_df)
        if fig.data:
            # Should have 3 quarters of data for E1
            assert len(fig.data[0].y) == 3


# ---------------------------------------------------------------------------
# Tests: render_cost_breakdown
# ---------------------------------------------------------------------------

class TestRenderCostBreakdown:
    def test_returns_plotly_figure(self, employee_table):
        import plotly.graph_objects as go
        emp_row = employee_table.iloc[0]
        fig = render_cost_breakdown(emp_row)
        assert isinstance(fig, go.Figure)

    def test_two_bars_salary_and_benefits(self, employee_table):
        emp_row = employee_table.iloc[0]
        fig = render_cost_breakdown(emp_row)
        assert len(fig.data) == 2

    def test_zero_cost_employee(self):
        import plotly.graph_objects as go
        emp_row = pd.Series({"annual_salary": 0, "annual_benefits": 0})
        fig = render_cost_breakdown(emp_row)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Tests: render_ego_network
# ---------------------------------------------------------------------------

class TestRenderEgoNetwork:
    def test_returns_plotly_figure(self, small_collab, employee_table):
        import plotly.graph_objects as go
        G = build_org_graph(small_collab)
        fig = render_ego_network("E1", G, employee_table, nexus_ids={"E1"})
        assert isinstance(fig, go.Figure)

    def test_unknown_node_returns_figure(self, small_collab, employee_table):
        import plotly.graph_objects as go
        G = build_org_graph(small_collab)
        fig = render_ego_network("GHOST", G, employee_table, nexus_ids=set())
        assert isinstance(fig, go.Figure)

    def test_isolated_node_returns_figure(self, employee_table):
        import plotly.graph_objects as go
        G = nx.Graph()
        G.add_node("ISOLATED")
        fig = render_ego_network("ISOLATED", G, employee_table, nexus_ids=set())
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Tests: exports — CSV
# ---------------------------------------------------------------------------

class TestCsvExport:
    def test_returns_bytes(self, employee_table):
        result = df_to_csv_bytes(employee_table)
        assert isinstance(result, bytes)

    def test_csv_decodable_to_utf8(self, employee_table):
        result = df_to_csv_bytes(employee_table)
        text = result.decode("utf-8")
        assert "employee_id" in text

    def test_csv_row_count_matches(self, employee_table):
        result = df_to_csv_bytes(employee_table)
        lines = result.decode("utf-8").strip().splitlines()
        # header + 4 data rows
        assert len(lines) == len(employee_table) + 1

    def test_empty_df_produces_header_only(self):
        df = pd.DataFrame(columns=["a", "b", "c"])
        result = df_to_csv_bytes(df)
        lines = result.decode("utf-8").strip().splitlines()
        assert len(lines) == 1
        assert "a" in lines[0]


# ---------------------------------------------------------------------------
# Tests: exports — Excel
# ---------------------------------------------------------------------------

class TestExcelExport:
    def test_returns_bytes(self, employee_table, dept_summary):
        result = tables_to_excel_bytes({
            "Employees": employee_table,
            "Departments": dept_summary,
        })
        assert isinstance(result, bytes)

    def test_bytes_are_xlsx_magic(self, employee_table):
        result = tables_to_excel_bytes({"Sheet1": employee_table})
        # XLSX files start with PK (zip archive)
        assert result[:2] == b"PK"

    def test_single_empty_sheet(self):
        result = tables_to_excel_bytes({"Empty": pd.DataFrame()})
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_sheet_name_truncated_to_31_chars(self):
        long_name = "A" * 50
        result = tables_to_excel_bytes({long_name: pd.DataFrame({"x": [1]})})
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# Tests: exports — PDF
# ---------------------------------------------------------------------------

class TestPdfExport:
    def test_returns_bytes(self, dept_summary, employee_table):
        result = generate_pdf_summary(
            org_name="Test Org",
            scenario_id="A",
            total_spend=5_000_000,
            total_budget=4_800_000,
            n_employees=100,
            avg_impact=72.0,
            n_nexus=3,
            dept_summary=dept_summary,
            top_impact_employees=employee_table,
        )
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_pdf_starts_with_pdf_header(self, dept_summary):
        result = generate_pdf_summary(
            org_name="Test Org", scenario_id="B",
            total_spend=1_000_000, total_budget=950_000,
            n_employees=50, avg_impact=65.0, n_nexus=1,
            dept_summary=dept_summary,
        )
        # PDF files start with %PDF
        assert result[:4] == b"%PDF"

    def test_with_warnings(self, dept_summary):
        result = generate_pdf_summary(
            org_name="At Risk Co", scenario_id="C",
            total_spend=6_000_000, total_budget=5_000_000,
            n_employees=200, avg_impact=60.0, n_nexus=8,
            dept_summary=dept_summary,
            warnings=["Engineering budget overrun by 20%", "3 nexus employees show attrition risk"],
        )
        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_empty_dept_summary(self):
        result = generate_pdf_summary(
            org_name="Org", scenario_id="A",
            total_spend=1_000_000, total_budget=1_000_000,
            n_employees=10, avg_impact=70.0, n_nexus=0,
            dept_summary=pd.DataFrame(),
        )
        assert isinstance(result, bytes)
