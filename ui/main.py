"""EIBO — Employee Impact & Budget Optimizer.

Entry point: streamlit run ui/main.py
"""

import sys
from pathlib import Path

# Make project root importable when running with `streamlit run ui/main.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from ui.components.brand import inject_css, render_nav, render_footer
from ui.info_page import business_view, engineering_view
from ui import dashboard, simulator


# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="EIBO — Employee Impact & Budget Optimizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults = {
        "page": "info",
        "info_tab": "business",
        "demo_mode": True,
        "demo_scenario": "A",
        "demo_size": "medium",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

def _render_sidebar() -> None:
    with st.sidebar:
        # OPB monogram
        st.markdown(
            """
            <div style="padding:28px 20px 20px; border-bottom:1px solid rgba(255,255,255,0.1);">
              <span style="font-family:'Fraunces',Georgia,serif; font-size:22px;
                           font-weight:300; color:#fff;">O</span>
              <em style="font-family:'Fraunces',Georgia,serif; font-size:22px;
                         font-weight:300; font-style:italic; color:#E8C46A;">PB</em>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:8px;
                          letter-spacing:3px; text-transform:uppercase;
                          color:rgba(255,255,255,0.35); margin-top:6px;">
                EIBO Platform
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        # Page navigation
        pages = {
            "info":        "📋  Info",
            "dashboard":   "📊  Dashboard",
            "simulation":  "🎯  Simulation",
            "drilldown":   "🔍  Drill-Down",
            "scenarios":   "📁  Scenarios",
            "strategic":   "🗺  Strategic",
            "admin":       "⚙  Admin",
        }

        st.markdown(
            '<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:8px; '
            'letter-spacing:3px; text-transform:uppercase; color:rgba(255,255,255,0.3); '
            'padding:0 20px; margin-bottom:8px;">NAVIGATION</div>',
            unsafe_allow_html=True,
        )

        for page_key, label in pages.items():
            is_active = st.session_state.page == page_key
            btn_style = (
                "background:rgba(201,168,76,0.15); color:#E8C46A; border:none;"
                if is_active
                else "background:none; color:rgba(255,255,255,0.45); border:none;"
            )
            if st.button(
                label,
                key=f"nav_{page_key}",
                use_container_width=True,
                help=None,
            ):
                st.session_state.page = page_key
                st.rerun()

        st.markdown("<hr style='border-color:rgba(255,255,255,0.1); margin:16px 0;'>",
                    unsafe_allow_html=True)

        # Demo mode controls
        st.markdown(
            '<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:8px; '
            'letter-spacing:3px; text-transform:uppercase; color:rgba(255,255,255,0.3); '
            'padding:0 20px; margin-bottom:8px;">DEMO MODE</div>',
            unsafe_allow_html=True,
        )

        demo_on = st.toggle("Use demo data", value=st.session_state.demo_mode)
        if demo_on != st.session_state.demo_mode:
            st.session_state.demo_mode = demo_on
            st.rerun()

        if st.session_state.demo_mode:
            scenario = st.selectbox(
                "Scenario",
                options=["A — Growing Company", "B — Restructuring", "C — Merger Integration"],
                index=["A", "B", "C"].index(st.session_state.demo_scenario),
            )
            st.session_state.demo_scenario = scenario[0]

            size = st.selectbox(
                "Org size",
                options=["Small (50 emp)", "Medium (500 emp)", "Large (5,000 emp)"],
                index=["small", "medium", "large"].index(st.session_state.demo_size),
            )
            st.session_state.demo_size = size.split(" ")[0].lower()

        else:
            st.markdown(
                '<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:11px; '
                'color:rgba(255,255,255,0.4); padding:0 4px; line-height:1.6;">'
                'Upload your data file via the Dashboard page.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='border-color:rgba(255,255,255,0.1); margin:16px 0;'>",
                    unsafe_allow_html=True)

        # Sprint status badge
        _sprint_status()


def _sprint_status() -> None:
    sprints = [
        ("Sprint 1", "Foundation", "completed"),
        ("Sprint 2", "Analytics", "completed"),
        ("Sprint 3", "Simulation", "completed"),
        ("Sprint 4", "Drill-Down", "pending"),
        ("Sprint 5", "Predictive", "pending"),
        ("Sprint 6", "Strategic", "pending"),
        ("Sprint 7", "Enterprise", "pending"),
    ]
    st.markdown(
        '<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:8px; '
        'letter-spacing:3px; text-transform:uppercase; color:rgba(255,255,255,0.3); '
        'padding:0 20px; margin-bottom:8px;">SPRINT STATUS</div>',
        unsafe_allow_html=True,
    )
    status_colors = {
        "completed":    ("#27B97C", "✓"),
        "in_progress":  ("#C8982A", "→"),
        "pending":      ("rgba(255,255,255,0.2)", "·"),
    }
    for sprint, desc, status in sprints:
        color, icon = status_colors[status]
        st.markdown(
            f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:10px; '
            f'color:{color}; padding:2px 20px; line-height:1.8;">'
            f'{icon} {sprint}: {desc}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------

def _render_info_page() -> None:
    # Tab switcher for Business / Engineering views
    hero_bg = (
        "background-color:#003366; background-image:"
        "linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),"
        "linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);"
        "background-size:48px 48px;"
    )
    st.markdown(
        f"""
        <div style="{hero_bg} padding:0;">
          <div style="max-width:1200px; margin:0 auto; padding:24px 48px 0;">
            <div style="display:flex; gap:4px; border-bottom:1px solid rgba(255,255,255,0.1);">
        """,
        unsafe_allow_html=True,
    )

    col_bus, col_eng, _ = st.columns([1.5, 1.5, 8])
    with col_bus:
        if st.button(
            "Business View",
            key="tab_business",
            use_container_width=True,
            type="primary" if st.session_state.info_tab == "business" else "secondary",
        ):
            st.session_state.info_tab = "business"
            st.rerun()

    with col_eng:
        if st.button(
            "Engineering View",
            key="tab_engineering",
            use_container_width=True,
            type="primary" if st.session_state.info_tab == "engineering" else "secondary",
        ):
            st.session_state.info_tab = "engineering"
            st.rerun()

    st.markdown("</div></div></div>", unsafe_allow_html=True)

    if st.session_state.info_tab == "business":
        business_view.render()
    else:
        engineering_view.render()


def _render_coming_soon(page_name: str, sprint: str, sprint_num: str) -> None:
    st.markdown(
        f"""
        <div style="background-color:#003366; background-image:
          linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
          background-size:48px 48px; padding:80px 48px; text-align:center;">
          <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                      font-weight:700; letter-spacing:4px; text-transform:uppercase;
                      color:rgba(255,255,255,0.35); margin-bottom:16px;">
            {sprint_num.upper()}
          </div>
          <h1 style="font-family:'Fraunces',Georgia,serif; font-size:32px;
                     font-weight:300; color:#fff; margin:0 0 12px;">
            {page_name} — <em style="color:#E8C46A; font-style:italic;">coming soon</em>
          </h1>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:14px;
                    color:rgba(255,255,255,0.6); max-width:480px; margin:0 auto;">
            This module is scheduled for {sprint}. The Info page is fully
            functional — explore the platform capabilities there.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "📋 While this page is under development, use the **Info** page to explore "
        "platform capabilities and the Business / Engineering views.",
        icon="ℹ️",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    inject_css()
    _render_sidebar()

    page = st.session_state.page

    if page == "info":
        _render_info_page()
    elif page == "dashboard":
        dashboard.render()
    elif page == "simulation":
        simulator.render()
    elif page == "drilldown":
        _render_coming_soon("Drill-Down Explorer", "Sprint 4", "sprint 4 · weeks 7–8")
    elif page == "scenarios":
        simulator.render()  # scenario manager is embedded in the simulator page
    elif page == "strategic":
        _render_coming_soon("Strategic Planner", "Sprint 6", "sprint 6 · weeks 11–12")
    elif page == "admin":
        _render_coming_soon("Admin Panel", "Sprint 7", "sprint 7 · weeks 13–14")

    render_footer()


if __name__ == "__main__":
    main()
