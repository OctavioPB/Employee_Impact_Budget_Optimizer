"""EIBO — Employee Impact & Budget Optimizer.

Entry point: streamlit run ui/main.py

Navigation model (UI_Decisions.md §7):
  - Sticky top nav bar: OPB monogram | app title | page links | theme toggle
  - Info/Overview page is standalone full-screen (nav hidden, its own bar)
  - No sidebar — navigation lives entirely in the top bar
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from ui.components.brand import inject_css, render_footer
from ui.info_page import business_view, engineering_view
from ui import dashboard, simulator, drilldown, predictive, strategic, admin, notifications_ui


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="EIBO — Employee Impact & Budget Optimizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "page":          "info",
    "theme":         "light",
    "demo_mode":     True,
    "demo_scenario": "A",
    "demo_size":     "small",
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ---------------------------------------------------------------------------
# Navigation — top bar pages (UI_Decisions.md §7)
#
# Pages listed here appear in the top nav bar.
# The info/overview page is reached via the "Overview" link at the end.
# ---------------------------------------------------------------------------

_NAV_PAGES = [
    ("dashboard",     "Dashboard"),
    ("simulation",    "Simulation"),
    ("drilldown",     "Drill-Down"),
    ("predictive",    "Predictive"),
    ("strategic",     "Strategic"),
    ("notifications", "Alerts"),
    ("admin",         "Admin"),
    ("info",          "Overview"),
]


# ---------------------------------------------------------------------------
# Top navigation bar
# UI_Decisions.md §7: sticky 52px navy bar, OPB monogram left, links right,
# active link = gold-light + rgba(201,168,76,0.12) background.
# Sentinel div enables CSS targeting of the following Streamlit element.
# ---------------------------------------------------------------------------

def _render_top_nav() -> None:
    # Sentinel marker — CSS uses `.opb-nav-sentinel + div` to style the
    # Streamlit block that immediately follows this element.
    st.markdown('<div class="opb-nav-sentinel"></div>', unsafe_allow_html=True)

    # Column proportions:
    # [monogram=2] [title=5] [nav×8 each=2] [theme=1] [demo-badge=2]
    nav_col_weights = [2] * len(_NAV_PAGES)
    col_widths = [2, 5] + nav_col_weights + [1, 2]
    cols = st.columns(col_widths)

    # ── OPB monogram (UI_Decisions.md §7 — Fraunces, O white / PB gold italic)
    with cols[0]:
        st.markdown(
            """
            <div style="display:flex;align-items:baseline;gap:1px;padding-left:4px;">
              <span style="font-family:'Fraunces',Georgia,serif;font-size:20px;
                           font-weight:300;color:#fff;line-height:1;">O</span>
              <em style="font-family:'Fraunces',Georgia,serif;font-size:20px;
                         font-weight:300;font-style:italic;color:#e8c46a;line-height:1;">PB</em>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── App title (9px uppercase, muted)
    with cols[1]:
        st.markdown(
            """
            <span style="font-family:'Plus Jakarta Sans',sans-serif;font-size:9px;
                         letter-spacing:3px;text-transform:uppercase;
                         color:rgba(255,255,255,0.4);">
              EMPLOYEE IMPACT &amp; BUDGET OPTIMIZER
            </span>
            """,
            unsafe_allow_html=True,
        )

    # ── Nav page links
    page = st.session_state.page
    for i, (key, label) in enumerate(_NAV_PAGES):
        with cols[2 + i]:
            if page == key:
                # Active: styled HTML div (non-interactive, already here)
                st.markdown(
                    f'<div class="opb-nav-active">{label}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(label, key=f"nav_{key}"):
                    st.session_state.page = key
                    st.rerun()

    # ── Theme toggle (◑ Dark / ☀ Light)
    with cols[-2]:
        theme = st.session_state.theme
        icon = "☀" if theme == "dark" else "◑"
        if st.button(icon, key="nav_theme_toggle"):
            st.session_state.theme = "dark" if theme == "light" else "light"
            st.rerun()

    # ── Demo mode badge
    with cols[-1]:
        if st.session_state.demo_mode:
            st.markdown(
                '<span style="font-family:\'Plus Jakarta Sans\',sans-serif;'
                'font-size:8px;letter-spacing:2px;text-transform:uppercase;'
                'color:rgba(232,196,106,0.55);white-space:nowrap;">DEMO</span>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Demo data controls — rendered as a compact bar below the nav on app pages
# ---------------------------------------------------------------------------

def _render_demo_controls() -> None:
    """Compact demo scenario / size selector strip (app pages only)."""
    if not st.session_state.demo_mode:
        return

    st.markdown(
        '<div style="background:rgba(0,51,102,0.06);border-bottom:1px solid #e0eaf4;'
        'padding:6px 40px;display:flex;align-items:center;gap:8px;">'
        '<span style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:8px;'
        'letter-spacing:2px;text-transform:uppercase;color:#6b7280;">DEMO DATA</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, _ = st.columns([1, 2, 2, 8])
    with c1:
        st.markdown(
            '<span style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            'letter-spacing:1px;text-transform:uppercase;color:#6b7280;'
            'display:block;padding-top:8px;">Scenario</span>',
            unsafe_allow_html=True,
        )
    with c2:
        scenario = st.selectbox(
            "Scenario",
            options=["A — Growing Company", "B — Restructuring", "C — Merger Integration"],
            index=["A", "B", "C"].index(st.session_state.demo_scenario),
            label_visibility="collapsed",
            key="demo_scenario_select",
        )
        st.session_state.demo_scenario = scenario[0]
    with c3:
        size = st.selectbox(
            "Org size",
            options=["Small (50 emp)", "Medium (500 emp)", "Large (5,000 emp)"],
            index=["small", "medium", "large"].index(st.session_state.demo_size),
            label_visibility="collapsed",
            key="demo_size_select",
        )
        st.session_state.demo_size = size.split(" ")[0].lower()


# ---------------------------------------------------------------------------
# Info / Overview page — standalone, full-screen
# No top nav bar. Has its own brand header + tab bar.
# UI_Decisions.md §8 tab bar pattern: borderBottom with gold-light on active.
# ---------------------------------------------------------------------------

_INFO_NAV_HTML = """
<div style="
  background: rgba(0,51,102,0.97);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  padding: 0 40px;
  height: 52px;
  position: sticky;
  top: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: space-between;
">
  <div style="display:flex;align-items:baseline;gap:1px;">
    <span style="font-family:'Fraunces',Georgia,serif;font-size:20px;
                 font-weight:300;color:#fff;line-height:1;">O</span>
    <em style="font-family:'Fraunces',Georgia,serif;font-size:20px;
               font-weight:300;font-style:italic;color:#e8c46a;line-height:1;">PB</em>
  </div>
  <span style="font-family:'Plus Jakarta Sans',sans-serif;font-size:9px;
               letter-spacing:3px;text-transform:uppercase;
               color:rgba(255,255,255,0.4);">
    EMPLOYEE IMPACT &amp; BUDGET OPTIMIZER &nbsp;&middot;&nbsp; PLATFORM OVERVIEW
  </span>
  <span style="font-family:'Plus Jakarta Sans',sans-serif;font-size:8px;
               letter-spacing:2px;text-transform:uppercase;
               color:rgba(232,196,106,0.4);">
    EIBO v1.0
  </span>
</div>
"""

def _render_info() -> None:
    """Standalone full-screen Overview page — its own brand header, no app nav."""
    # Own decorative nav bar (HTML, not interactive)
    st.markdown(_INFO_NAV_HTML, unsafe_allow_html=True)

    # Launch application CTA — right-aligned below the nav bar
    _, cta_col = st.columns([5, 1])
    with cta_col:
        st.markdown(
            """
            <style>
            div[data-testid="column"]:last-child .stButton > button {
              background-color: #c8982a !important;
              color: #fff !important;
              border: none !important;
              font-weight: 700 !important;
              font-size: 9px !important;
              letter-spacing: 1.5px !important;
              margin-top: 10px;
            }
            div[data-testid="column"]:last-child .stButton > button:hover {
              background-color: #e8c46a !important;
              color: #003366 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Application →", key="info_launch_app", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

    # Tab bar — Business View / Engineering View
    # UI_Decisions.md §8: tab bar at bottom of hero merges with content below
    tab_b, tab_e = st.tabs(["  Business View  ", "  Engineering View  "])
    with tab_b:
        business_view.render()
    with tab_e:
        engineering_view.render()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    inject_css()

    page = st.session_state.page

    # Info / Overview page: standalone full-screen, its own nav bar, no top nav
    if page == "info":
        _render_info()
        render_footer()
        return

    # All other pages: sticky top nav + demo controls strip
    _render_top_nav()
    _render_demo_controls()

    if page == "dashboard":
        dashboard.render()
    elif page == "simulation":
        simulator.render()
    elif page == "drilldown":
        drilldown.render()
    elif page == "predictive":
        predictive.render()
    elif page == "strategic":
        strategic.render()
    elif page == "notifications":
        notifications_ui.render()
    elif page == "admin":
        admin.render()

    render_footer()


if __name__ == "__main__":
    main()
