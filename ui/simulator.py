"""Budget Simulation page — Sprint 3: Optimization Engine & Simulation.

Layout:
  1. Hero — org spend context, budget slider, constraint toggles
  2. Solve results — KPI strip, retained list, at-risk list
  3. Human-in-the-loop override panel + cascade warning
  4. Before/After comparison (budget, headcount, skills)
  5. Sensitivity analysis chart
  6. What-if scenario manager
"""

import json
import logging
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from optimization_engine.constraints import ConstraintConfig
from optimization_engine.ilp_solver import OptimizationResult, solve
from optimization_engine.sensitivity import run_sensitivity
from ui.data_loader import DashboardData, load_dashboard_data

logger = logging.getLogger(__name__)

_COLORS = dict(
    primary="#003366", green="#27B97C", purple="#7C4DBD",
    orange="#F07020", gold="#C8982A", gold_lt="#E8C46A",
    light="#F4F6F9", mid="#6B7280", dark="#1C1C2E", white="#FFFFFF",
)
_FONT = "'Plus Jakarta Sans', sans-serif"

# Max scenarios the manager stores
_MAX_SCENARIOS = 5

# ---------------------------------------------------------------------------
# Session-state management
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "sim_budget_pct": 90.0,
    "sim_force_retain": set(),
    "sim_exclude": set(),
    "sim_notes": {},          # employee_id → str annotation
    "sim_audit": [],          # list of audit log dicts
    "sim_undo_stack": [],     # list of (force_retain, exclude, notes) snapshots
    "sim_scenarios": [],      # saved scenarios
    "sim_leadership": True,
    "sim_skills": True,
    "sim_succession": False,
}


def _init() -> None:
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _push_undo() -> None:
    snapshot = (
        set(st.session_state.sim_force_retain),
        set(st.session_state.sim_exclude),
        dict(st.session_state.sim_notes),
    )
    stack: list = st.session_state.sim_undo_stack
    stack.append(snapshot)
    if len(stack) > 20:
        stack.pop(0)


def _apply_override(emp_id: str, action: str, note: str = "") -> None:
    """Add a force-retain or exclude override, log it, and push undo snapshot."""
    _push_undo()

    fr: set = st.session_state.sim_force_retain
    ex: set = st.session_state.sim_exclude
    notes: dict = st.session_state.sim_notes

    if action == "force_retain":
        fr.add(emp_id)
        ex.discard(emp_id)
    elif action == "exclude":
        ex.add(emp_id)
        fr.discard(emp_id)
    elif action == "clear":
        fr.discard(emp_id)
        ex.discard(emp_id)
        notes.pop(emp_id, None)

    if note:
        notes[emp_id] = note

    st.session_state.sim_audit.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "employee_id": emp_id,
        "action": action,
        "note": note,
    })


def _undo() -> None:
    stack: list = st.session_state.sim_undo_stack
    if stack:
        fr, ex, notes = stack.pop()
        st.session_state.sim_force_retain = fr
        st.session_state.sim_exclude = ex
        st.session_state.sim_notes = notes


# ---------------------------------------------------------------------------
# Solver preparation
# ---------------------------------------------------------------------------

def _build_critical_skill_holders(data: DashboardData) -> dict[str, list[str]]:
    if data.skills.empty or data.employee_skills.empty:
        return {}
    critical_skills = data.skills[data.skills["is_critical"] == True]
    result: dict[str, list[str]] = {}
    for _, skill in critical_skills.iterrows():
        holders = data.employee_skills[
            data.employee_skills["skill_id"] == skill["skill_id"]
        ]["employee_id"].tolist()
        if holders:
            result[str(skill["skill_id"])] = holders
    return result


def _run_solve(data: DashboardData, budget_target: float) -> OptimizationResult:
    cfg = ConstraintConfig(
        require_leadership_per_team=st.session_state.sim_leadership,
        require_critical_skills=st.session_state.sim_skills,
        succession_depth=1 if st.session_state.sim_succession else 0,
        time_limit_seconds=30,
    )
    return solve(
        employees=data.employees,
        budget_target=budget_target,
        impact_scores=data.impact_scores,
        critical_skill_holders=_build_critical_skill_holders(data),
        constraint_config=cfg,
        force_retain=set(st.session_state.sim_force_retain),
        exclude=set(st.session_state.sim_exclude),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    _init()

    demo_mode: bool = st.session_state.get("demo_mode", True)
    scenario_id: str = st.session_state.get("demo_scenario", "A")
    size: str = st.session_state.get("demo_size", "medium")

    with st.spinner("Loading organization data…"):
        try:
            data = load_dashboard_data(demo_mode, scenario_id, size)
        except (NotImplementedError, RuntimeError) as exc:
            st.error(str(exc))
            return

    current_spend = data.total_spend
    budget_target = current_spend * st.session_state.sim_budget_pct / 100.0

    _render_hero(data, current_spend, budget_target)
    result = _render_controls_and_solve(data, current_spend)

    if result.status == "Optimal":
        _render_results_strip(result)
        col_ret, col_risk = st.columns(2, gap="large")
        with col_ret:
            _render_retained_table(data, result)
        with col_risk:
            _render_at_risk_table(data, result)
        _render_overrides_panel(data, result)
        _render_before_after(data, result)
        _render_sensitivity(data, current_spend, result)
    else:
        _render_infeasibility_panel(result)

    _render_scenario_manager(data, result, budget_target)


# ---------------------------------------------------------------------------
# 1. Hero
# ---------------------------------------------------------------------------

def _render_hero(data: DashboardData, current_spend: float, budget_target: float) -> None:
    variance_sign = "+" if data.budget_variance_pct >= 0 else ""
    st.markdown(
        f"""
        <div style="background:#003366;
          background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),
          linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);
          background-size:48px 48px; padding:48px 48px 32px;">
          <div style="max-width:1300px; margin:0 auto;">
            <h1 style="font-family:'Fraunces',Georgia,serif; font-size:30px; font-weight:300;
                       color:#fff; margin:0 0 8px;">
              Budget <em style="color:#E8C46A; font-style:italic;">Simulation</em>
            </h1>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                      color:rgba(255,255,255,.55); margin:0 0 28px; max-width:560px; line-height:1.75;">
              Model suggests which employees to retain under a given budget target.
              Every recommendation is adjustable — the decision belongs to you.
            </p>
            <div style="display:flex; gap:36px; flex-wrap:wrap;">
              <div style="border-left:2px solid #C8982A; padding-left:16px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:30px; font-weight:300;
                            color:#E8C46A;">${current_spend/1e6:.2f}M</div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                            color:rgba(255,255,255,.5); margin-top:6px;">Current Payroll</div>
              </div>
              <div style="border-left:2px solid #C8982A; padding-left:16px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:30px; font-weight:300;
                            color:#E8C46A;">{data.total_headcount:,}</div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                            color:rgba(255,255,255,.5); margin-top:6px;">Active Employees</div>
              </div>
              <div style="border-left:2px solid #C8982A; padding-left:16px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:30px; font-weight:300;
                            color:#E8C46A;">{variance_sign}{data.budget_variance_pct:.1f}%</div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                            color:rgba(255,255,255,.5); margin-top:6px;">Spend vs Budget</div>
              </div>
              <div style="border-left:2px solid #C8982A; padding-left:16px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:30px; font-weight:300;
                            color:#E8C46A;">{data.avg_impact_score:.1f}</div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                            color:rgba(255,255,255,.5); margin-top:6px;">Avg Impact Score</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 2. Controls + solve
# ---------------------------------------------------------------------------

def _render_controls_and_solve(
    data: DashboardData, current_spend: float
) -> OptimizationResult:
    st.markdown("<div style='height:1px; background:#E0EAF4;'></div>", unsafe_allow_html=True)

    with st.container():
        st.markdown(
            """
            <div style="max-width:1300px; margin:0 auto; padding:32px 48px 0;">
              <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                          font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                          letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
                <div style="width:24px; height:1px; background:#C8982A;"></div>Budget Target
              </div>
              <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                         color:#0a1628; margin:0 0 16px;">
                Set the target and <em style="font-style:italic;">run the model</em>
              </h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_slider, col_constraints = st.columns([3, 1], gap="large")

    with col_slider:
        budget_pct = st.slider(
            "Budget target (% of current payroll)",
            min_value=50.0,
            max_value=120.0,
            value=float(st.session_state.sim_budget_pct),
            step=1.0,
            format="%.0f%%",
            help="Drag to set the simulation budget. 100% = current payroll spend.",
            key="sim_budget_slider",
        )
        st.session_state.sim_budget_pct = budget_pct
        budget_target = current_spend * budget_pct / 100.0

        # Quick presets
        p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
        for col, label, pct in [
            (p_col1, "−20%", 80.0), (p_col2, "−10%", 90.0), (p_col3, "−5%", 95.0),
            (p_col4, "Neutral", 100.0), (p_col5, "+10%", 110.0),
        ]:
            with col:
                if st.button(label, key=f"preset_{pct}", use_container_width=True):
                    st.session_state.sim_budget_pct = pct
                    st.rerun()

        st.markdown(
            f'<div style="font-family:{_FONT}; font-size:12px; color:#6B7280; margin-top:4px;">'
            f'Target: <strong style="color:#003366;">${budget_target/1e6:.2f}M</strong>'
            f' — Savings target: <strong style="color:#F07020;">'
            f'${(current_spend - budget_target)/1e6:.2f}M</strong>'
            f' ({(current_spend - budget_target)/current_spend*100:.1f}% reduction)</div>',
            unsafe_allow_html=True,
        )

    with col_constraints:
        st.markdown(
            f'<div style="font-family:{_FONT}; font-size:9px; font-weight:700; '
            f'letter-spacing:3px; text-transform:uppercase; color:#003366; margin-bottom:8px;">'
            f'Constraints</div>',
            unsafe_allow_html=True,
        )
        st.session_state.sim_leadership = st.checkbox(
            "Leadership per team", value=st.session_state.sim_leadership
        )
        st.session_state.sim_skills = st.checkbox(
            "Critical skill coverage", value=st.session_state.sim_skills
        )
        st.session_state.sim_succession = st.checkbox(
            "Succession backup (+1 holder)", value=st.session_state.sim_succession
        )

        st.markdown("<br>", unsafe_allow_html=True)
        n_fr = len(st.session_state.sim_force_retain)
        n_ex = len(st.session_state.sim_exclude)
        if n_fr + n_ex > 0:
            st.markdown(
                f'<div style="font-family:{_FONT}; font-size:11px; color:#6B7280;">'
                f'Overrides active: {n_fr} Force Retain · {n_ex} Exclude</div>',
                unsafe_allow_html=True,
            )
            if st.button("Undo last override", use_container_width=True):
                _undo()
                st.rerun()
            if st.button("Clear all overrides", use_container_width=True):
                _push_undo()
                st.session_state.sim_force_retain = set()
                st.session_state.sim_exclude = set()
                st.session_state.sim_notes = {}
                st.rerun()

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px 0;'></div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Optimizing workforce allocation…"):
        result = _run_solve(data, budget_target)

    return result


# ---------------------------------------------------------------------------
# 3. Result KPI strip
# ---------------------------------------------------------------------------

def _render_results_strip(result: OptimizationResult) -> None:
    savings_color = _COLORS["green"] if result.budget_savings >= 0 else _COLORS["orange"]
    impact_delta_color = _COLORS["green"] if result.impact_delta >= 0 else _COLORS["orange"]
    kl_color = _COLORS["orange"] if result.knowledge_loss_score > 0.3 else _COLORS["green"]

    st.markdown(
        f"""
        <div style="background:#fff; border-top:3px solid #C8982A;
                    box-shadow:0 1px 4px rgba(0,51,102,0.08);
                    padding:24px 48px; margin-bottom:0;">
          <div style="max-width:1300px; margin:0 auto;
                      display:flex; gap:32px; flex-wrap:wrap; align-items:flex-start;">
            <div style="text-align:center; min-width:110px;">
              <div style="font-family:'Fraunces',Georgia,serif; font-size:34px; font-weight:300;
                          color:#003366; line-height:1;">{result.n_retained}</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:700;
                          letter-spacing:2px; text-transform:uppercase; color:#6B7280; margin-top:6px;">
                Suggested Retention
              </div>
            </div>
            <div style="text-align:center; min-width:110px;">
              <div style="font-family:'Fraunces',Georgia,serif; font-size:34px; font-weight:300;
                          color:{_COLORS['orange']}; line-height:1;">{result.n_at_risk}</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:700;
                          letter-spacing:2px; text-transform:uppercase; color:#6B7280; margin-top:6px;">
                Under Review
              </div>
            </div>
            <div style="text-align:center; min-width:130px;">
              <div style="font-family:'Fraunces',Georgia,serif; font-size:34px; font-weight:300;
                          color:{savings_color}; line-height:1;">
                ${result.budget_savings/1e6:.2f}M
              </div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:700;
                          letter-spacing:2px; text-transform:uppercase; color:#6B7280; margin-top:6px;">
                Annual Savings ({result.savings_pct:.1f}%)
              </div>
            </div>
            <div style="text-align:center; min-width:120px;">
              <div style="font-family:'Fraunces',Georgia,serif; font-size:34px; font-weight:300;
                          color:{impact_delta_color}; line-height:1;">
                {'+' if result.impact_delta >= 0 else ''}{result.impact_delta:.1f}
              </div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:700;
                          letter-spacing:2px; text-transform:uppercase; color:#6B7280; margin-top:6px;">
                Impact Δ vs Baseline
              </div>
            </div>
            <div style="text-align:center; min-width:120px;">
              <div style="font-family:'Fraunces',Georgia,serif; font-size:34px; font-weight:300;
                          color:{kl_color}; line-height:1;">
                {result.knowledge_loss_score*100:.0f}%
              </div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:700;
                          letter-spacing:2px; text-transform:uppercase; color:#6B7280; margin-top:6px;">
                Knowledge at Risk
              </div>
            </div>
            <div style="text-align:center; min-width:120px;">
              <div style="font-family:'Fraunces',Georgia,serif; font-size:34px; font-weight:300;
                          color:{_COLORS['green'] if not result.critical_skills_lost else _COLORS['orange']};
                          line-height:1;">
                {len(result.critical_skills_lost)}
              </div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:700;
                          letter-spacing:2px; text-transform:uppercase; color:#6B7280; margin-top:6px;">
                Critical Skills Lost
              </div>
            </div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                        color:#9CA3AF; align-self:center; margin-left:auto;">
              Solved in {result.solver_time_ms:.0f}ms · {result.force_retain_count} forced ·
              {result.exclude_count} excluded
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.critical_skills_lost:
        st.warning(
            f"⚠ Critical skills not covered at this budget level: "
            + ", ".join(result.critical_skills_lost[:5])
            + ("…" if len(result.critical_skills_lost) > 5 else "")
        )
    if result.teams_with_no_leader:
        st.warning(
            f"⚠ Teams without a retained leader: "
            + ", ".join(result.teams_with_no_leader[:5])
            + ("…" if len(result.teams_with_no_leader) > 5 else "")
        )


# ---------------------------------------------------------------------------
# 4a. Retained table
# ---------------------------------------------------------------------------

def _render_retained_table(data: DashboardData, result: OptimizationResult) -> None:
    st.markdown(
        """
        <div style="padding:24px 0 8px 48px;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#27B97C;">
            <div style="width:24px; height:1px; background:#27B97C;"></div>Suggested Retention
          </div>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px; color:#6B7280; margin:0;">
            Model recommends retaining these employees at this budget level.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    retained = data.employee_table[
        data.employee_table["employee_id"].isin(result.retained_ids)
    ].head(15).copy()

    if retained.empty:
        st.info("No employees in retention list.")
        return

    retained["★"] = retained["is_nexus"].map({True: "★", False: ""})
    display = retained[["★", "full_name", "role_title", "department",
                         "impact_score", "confidence"]].copy()
    display.columns = ["", "Employee", "Role", "Dept", "Impact", "Confidence"]
    display["Impact"] = display["Impact"].apply(lambda v: f"{v:.1f}")
    display["Confidence"] = display["Confidence"].apply(lambda v: f"{v:.0%}")

    st.dataframe(display, hide_index=True, use_container_width=True,
                 height=min(400, 40 + 35 * len(display)))

    # Override controls
    with st.expander("Add override for a retained employee"):
        _override_form(data, "retained", result)


# ---------------------------------------------------------------------------
# 4b. At-risk table
# ---------------------------------------------------------------------------

def _render_at_risk_table(data: DashboardData, result: OptimizationResult) -> None:
    st.markdown(
        """
        <div style="padding:24px 0 8px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#F07020;">
            <div style="width:24px; height:1px; background:#F07020;"></div>Under Review
          </div>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px; color:#6B7280; margin:0;">
            Not prioritized by the model at this budget. Review before deciding.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    at_risk = data.employee_table[
        data.employee_table["employee_id"].isin(result.at_risk_ids)
    ].head(15).copy()

    if at_risk.empty:
        st.success("All employees are in the retention list at this budget level.")
        return

    at_risk["★"] = at_risk["is_nexus"].map({True: "★", False: ""})
    display = at_risk[["★", "full_name", "role_title", "department",
                        "impact_score", "confidence"]].copy()
    display.columns = ["", "Employee", "Role", "Dept", "Impact", "Confidence"]
    display["Impact"] = display["Impact"].apply(lambda v: f"{v:.1f}")
    display["Confidence"] = display["Confidence"].apply(lambda v: f"{v:.0%}")

    st.dataframe(display, hide_index=True, use_container_width=True,
                 height=min(400, 40 + 35 * len(display)))

    with st.expander("Add override for an at-risk employee"):
        _override_form(data, "at_risk", result)


def _override_form(data: DashboardData, pool: str, result: OptimizationResult) -> None:
    """Selectbox + override action + annotation for one employee."""
    if pool == "retained":
        ids = list(result.retained_ids)
    else:
        ids = list(result.at_risk_ids)

    name_map = dict(zip(data.employees["employee_id"], data.employees["full_name"]))
    options = sorted([name_map.get(i, i) for i in ids])
    id_map = {v: k for k, v in name_map.items()}

    selected_name = st.selectbox(
        "Select employee", options,
        key=f"override_sel_{pool}", label_visibility="collapsed"
    )
    emp_id = id_map.get(selected_name, selected_name)

    note = st.text_input(
        "Annotation (e.g. 'Critical project until Q3')",
        key=f"override_note_{pool}",
        placeholder="Optional reason for this override…",
        label_visibility="collapsed",
    )

    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        if st.button("Force Retain", key=f"btn_fr_{pool}", use_container_width=True):
            _apply_override(emp_id, "force_retain", note)
            st.rerun()
    with oc2:
        if st.button("Exclude", key=f"btn_ex_{pool}", use_container_width=True):
            _apply_override(emp_id, "exclude", note)
            st.rerun()
    with oc3:
        if st.button("Clear Override", key=f"btn_cl_{pool}", use_container_width=True):
            _apply_override(emp_id, "clear")
            st.rerun()


# ---------------------------------------------------------------------------
# 5. Override audit panel + cascade warning
# ---------------------------------------------------------------------------

def _render_overrides_panel(data: DashboardData, result: OptimizationResult) -> None:
    fr: set = st.session_state.sim_force_retain
    ex: set = st.session_state.sim_exclude
    notes: dict = st.session_state.sim_notes

    if not fr and not ex:
        return

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:8px 48px;'></div>",
        unsafe_allow_html=True,
    )

    name_map = dict(zip(data.employees["employee_id"], data.employees["full_name"]))

    with st.expander(
        f"Override panel — {len(fr)} Force Retain · {len(ex)} Excluded", expanded=True
    ):
        if fr:
            st.markdown(
                '<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:9px; '
                'font-weight:700; letter-spacing:2px; text-transform:uppercase; '
                'color:#27B97C; margin-bottom:6px;">Force Retained</div>',
                unsafe_allow_html=True,
            )
            for eid in sorted(fr):
                name = name_map.get(eid, eid)
                note = notes.get(eid, "")
                note_str = f' — "{note}"' if note else ""
                st.markdown(
                    f'<div style="font-family:{_FONT}; font-size:12px; color:#1C1C2E; '
                    f'padding:4px 0;">✓ <strong>{name}</strong>{note_str}</div>',
                    unsafe_allow_html=True,
                )

        if ex:
            st.markdown(
                '<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:9px; '
                'font-weight:700; letter-spacing:2px; text-transform:uppercase; '
                'color:#6B7280; margin-top:12px; margin-bottom:6px;">Excluded</div>',
                unsafe_allow_html=True,
            )
            for eid in sorted(ex):
                name = name_map.get(eid, eid)
                note = notes.get(eid, "")
                note_str = f' — "{note}"' if note else ""
                st.markdown(
                    f'<div style="font-family:{_FONT}; font-size:12px; color:#6B7280; '
                    f'padding:4px 0;">○ {name}{note_str}</div>',
                    unsafe_allow_html=True,
                )

        # Batch operations
        st.markdown("<br>", unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            dept_options = ["— batch by department —"] + sorted(
                data.employees["department"].unique().tolist()
            )
            dept_sel = st.selectbox("Force-retain entire department", dept_options,
                                    key="batch_dept_fr", label_visibility="collapsed")
        with bc2:
            if st.button("Apply Force Retain to Dept", use_container_width=True,
                         key="btn_batch_fr"):
                if dept_sel != "— batch by department —":
                    dept_emps = data.employees[
                        data.employees["department"] == dept_sel
                    ]["employee_id"].tolist()
                    _push_undo()
                    for eid in dept_emps:
                        st.session_state.sim_force_retain.add(eid)
                        st.session_state.sim_exclude.discard(eid)
                    st.session_state.sim_audit.append({
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "employee_id": "BATCH",
                        "action": f"force_retain_dept:{dept_sel}",
                        "note": f"{len(dept_emps)} employees",
                    })
                    st.rerun()

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:8px 48px;'></div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 6. Before / After comparison
# ---------------------------------------------------------------------------

def _render_before_after(data: DashboardData, result: OptimizationResult) -> None:
    st.markdown(
        """
        <div style="max-width:1300px; margin:0 auto; padding:24px 48px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A;"></div>Before / After
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 20px;">
            Organizational impact of the <em style="font-style:italic;">simulation</em>
          </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        _render_waterfall(data, result)

    with col2:
        _render_dept_impact_delta(data, result)

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px;'></div>",
        unsafe_allow_html=True,
    )


def _render_waterfall(data: DashboardData, result: OptimizationResult) -> None:
    """Waterfall: Current Spend → Savings by department → Optimized Cost."""
    dept_savings: dict[str, float] = {}
    emp_team_map = dict(zip(data.employees["employee_id"], data.employees["team_id"]))
    team_dept_map = dict(zip(data.teams["team_id"], data.teams["department"]))

    for eid in result.at_risk_ids:
        team_id = emp_team_map.get(eid, "")
        dept = team_dept_map.get(team_id, "Other")
        cost = float(
            data.employees[data.employees["employee_id"] == eid]
            [["annual_salary", "annual_benefits"]].sum(axis=1).sum()
        )
        dept_savings[dept] = dept_savings.get(dept, 0.0) + cost

    categories = ["Current Spend"] + list(dept_savings.keys()) + ["Optimized Cost"]
    values = [result.current_spend] + [-v for v in dept_savings.values()] + [result.total_cost]
    measure = ["absolute"] + ["relative"] * len(dept_savings) + ["total"]
    text = [
        f"${result.current_spend/1e6:.2f}M",
        *[f"−${v/1e6:.2f}M" for v in dept_savings.values()],
        f"${result.total_cost/1e6:.2f}M",
    ]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measure,
        x=categories,
        y=values,
        text=text,
        textposition="outside",
        decreasing=dict(marker_color=_COLORS["green"]),
        increasing=dict(marker_color=_COLORS["orange"]),
        totals=dict(marker_color=_COLORS["primary"]),
        connector=dict(line=dict(color="#E0EAF4", width=1)),
    ))

    fig.add_hline(
        y=result.budget_target,
        line_dash="dash", line_color=_COLORS["gold"], line_width=2,
        annotation_text=f"Target ${result.budget_target/1e6:.2f}M",
        annotation_font_color=_COLORS["gold"],
    )

    fig.update_layout(
        font_family=_FONT, paper_bgcolor=_COLORS["light"], plot_bgcolor="white",
        margin=dict(l=16, r=16, t=32, b=16),
        height=320, showlegend=False,
        yaxis=dict(tickprefix="$", ticksuffix="", tickformat=".2s",
                   gridcolor="#E0EAF4", zeroline=False),
        xaxis=dict(showgrid=False, tickangle=-20),
    )
    st.plotly_chart(fig, use_container_width=True, key="waterfall")


def _render_dept_impact_delta(data: DashboardData, result: OptimizationResult) -> None:
    """Bar chart: per-department average impact change."""
    team_dept = dict(zip(data.teams["team_id"], data.teams["department"]))
    dept_delta: dict[str, list[float]] = {}

    for tid, delta in result.team_impact_change.items():
        dept = team_dept.get(str(tid), "Other")
        dept_delta.setdefault(dept, []).append(delta)

    if not dept_delta:
        return

    dept_avg = {dept: sum(vals) / len(vals) for dept, vals in dept_delta.items()}
    df = pd.DataFrame(list(dept_avg.items()), columns=["Department", "Impact Delta"])
    df = df.sort_values("Impact Delta")

    fig = go.Figure(go.Bar(
        x=df["Impact Delta"],
        y=df["Department"],
        orientation="h",
        marker_color=[
            _COLORS["green"] if v >= 0 else _COLORS["orange"]
            for v in df["Impact Delta"]
        ],
        text=df["Impact Delta"].apply(lambda v: f"{'+' if v >= 0 else ''}{v:.1f}"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Impact Δ: %{x:.2f}<extra></extra>",
    ))

    fig.update_layout(
        font_family=_FONT, paper_bgcolor=_COLORS["light"], plot_bgcolor="white",
        margin=dict(l=16, r=48, t=32, b=16),
        height=320, showlegend=False,
        xaxis=dict(title="Avg Impact Δ (retained vs all)", gridcolor="#E0EAF4", zeroline=True,
                   zerolinecolor="#E0EAF4"),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True, key="dept_delta")


# ---------------------------------------------------------------------------
# 7. Sensitivity analysis
# ---------------------------------------------------------------------------

def _render_sensitivity(
    data: DashboardData, current_spend: float, result: OptimizationResult
) -> None:
    st.markdown(
        """
        <div style="max-width:1300px; margin:0 auto; padding:0 48px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A;"></div>Sensitivity Analysis
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 8px;">
            How recommendations shift with <em style="font-style:italic;">budget variation</em>
          </h2>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                    color:#6B7280; margin:0 0 16px; line-height:1.7;">
            Each data point is an independent ILP solve at ±5%, ±10%, ±20% of the current budget target.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    base_budget = current_spend * st.session_state.sim_budget_pct / 100.0

    with st.spinner("Running sensitivity analysis…"):
        cfg = ConstraintConfig(
            require_leadership_per_team=st.session_state.sim_leadership,
            require_critical_skills=st.session_state.sim_skills,
            time_limit_seconds=15,
        )
        report = run_sensitivity(
            employees=data.employees,
            base_budget=base_budget,
            impact_scores=data.impact_scores,
            critical_skill_holders=_build_critical_skill_holders(data),
            constraint_config=cfg,
            force_retain=set(st.session_state.sim_force_retain),
            exclude=set(st.session_state.sim_exclude),
        )

    col_chart, col_table = st.columns([2, 1], gap="large")

    with col_chart:
        rows = [r for r in report.rows if r.status == "Optimal"]
        if rows:
            labels = [f"{'+' if r.delta_pct >= 0 else ''}{r.delta_pct*100:.0f}%" for r in rows]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=labels, y=[r.n_retained for r in rows],
                name="Retained", mode="lines+markers",
                line=dict(color=_COLORS["green"], width=2),
                marker=dict(size=8),
                yaxis="y1",
                hovertemplate="%{x}<br>Retained: %{y}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=labels, y=[r.total_impact for r in rows],
                name="Total Impact", mode="lines+markers",
                line=dict(color=_COLORS["primary"], width=2, dash="dot"),
                marker=dict(size=8),
                yaxis="y2",
                hovertemplate="%{x}<br>Impact: %{y:.1f}<extra></extra>",
            ))
            # Highlight base (delta = 0)
            base_label = "0%"
            if base_label in labels:
                fig.add_vline(
                    x=base_label, line_dash="dash", line_color=_COLORS["gold"],
                    annotation_text="Base", annotation_font_color=_COLORS["gold"],
                )
            fig.update_layout(
                font_family=_FONT, paper_bgcolor=_COLORS["light"], plot_bgcolor="white",
                margin=dict(l=16, r=60, t=32, b=16),
                height=280,
                yaxis=dict(title="Employees Retained", gridcolor="#E0EAF4", zeroline=False),
                yaxis2=dict(title="Total Impact", overlaying="y", side="right",
                            zeroline=False, showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True, key="sensitivity_chart")

    with col_table:
        df = report.as_dataframe
        st.dataframe(df, hide_index=True, use_container_width=True, height=290)

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px;'></div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 8. Infeasibility panel
# ---------------------------------------------------------------------------

def _render_infeasibility_panel(result: OptimizationResult) -> None:
    st.error(
        f"**Optimization infeasible** ({result.status}) — the model could not find a valid "
        "workforce plan with the current budget and constraints."
    )
    if result.infeasibility_reason:
        for line in result.infeasibility_reason.split(" | "):
            st.markdown(f"- {line}")

    st.info(
        "**To resolve:** Try (1) increasing the budget target, (2) disabling the leadership "
        "or skills constraint in the Constraints panel, or (3) removing Force Retain / Exclude overrides."
    )


# ---------------------------------------------------------------------------
# 9. Scenario manager
# ---------------------------------------------------------------------------

def _render_scenario_manager(
    data: DashboardData, result: OptimizationResult, budget_target: float
) -> None:
    st.markdown(
        """
        <div style="max-width:1300px; margin:0 auto; padding:0 48px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A;"></div>What-If Scenarios
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 8px;">
            Save and compare <em style="font-style:italic;">budget strategies</em>
          </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    scenarios: list[dict] = st.session_state.sim_scenarios

    # Save current scenario
    s_col1, s_col2, s_col3 = st.columns([2, 1, 1], gap="medium")
    with s_col1:
        scen_name = st.text_input(
            "Scenario name", placeholder="e.g. Conservative −10% cut",
            key="scen_name_input", label_visibility="collapsed"
        )
    with s_col2:
        if st.button("Save scenario", use_container_width=True, key="btn_save_scen",
                     disabled=not result.is_feasible):
            if scen_name and len(scenarios) < _MAX_SCENARIOS:
                scenarios.append({
                    "name": scen_name,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "budget_pct": st.session_state.sim_budget_pct,
                    "budget_target_M": round(budget_target / 1e6, 3),
                    "n_retained": result.n_retained,
                    "n_at_risk": result.n_at_risk,
                    "total_cost_M": round(result.total_cost / 1e6, 3),
                    "savings_pct": result.savings_pct,
                    "total_impact": round(result.total_impact, 2),
                    "avg_impact": round(result.avg_impact_retained, 2),
                    "skills_lost": len(result.critical_skills_lost),
                    "skills_preserved": len(result.critical_skills_preserved),
                    "force_retain": list(st.session_state.sim_force_retain),
                    "exclude": list(st.session_state.sim_exclude),
                    "leadership_constraint": st.session_state.sim_leadership,
                    "skills_constraint": st.session_state.sim_skills,
                })
                st.rerun()
            elif len(scenarios) >= _MAX_SCENARIOS:
                st.warning(f"Maximum {_MAX_SCENARIOS} scenarios stored. Clear one first.")

    with s_col3:
        if scenarios and st.button("Clear scenarios", use_container_width=True, key="btn_clr_scen"):
            st.session_state.sim_scenarios = []
            st.rerun()

    if not scenarios:
        st.markdown(
            f'<div style="font-family:{_FONT}; font-size:12px; color:#9CA3AF; margin:12px 0 32px;">'
            f'No scenarios saved yet. Run an optimization and click "Save scenario".</div>',
            unsafe_allow_html=True,
        )
        return

    # Side-by-side comparison table
    compare_cols = [
        "name", "budget_pct", "budget_target_M", "n_retained", "n_at_risk",
        "total_cost_M", "savings_pct", "total_impact", "avg_impact",
        "skills_lost", "skills_preserved",
    ]
    compare_df = pd.DataFrame(scenarios)[compare_cols].copy()
    compare_df.columns = [
        "Scenario", "Budget %", "Target ($M)", "Retained", "Under Review",
        "Cost ($M)", "Savings %", "Total Impact", "Avg Impact",
        "Skills Lost", "Skills Covered",
    ]
    compare_df["Budget %"] = compare_df["Budget %"].apply(lambda v: f"{v:.0f}%")
    compare_df["Savings %"] = compare_df["Savings %"].apply(lambda v: f"{v:.1f}%")

    st.dataframe(compare_df, hide_index=True, use_container_width=True)

    # Export
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        json_str = json.dumps(scenarios, indent=2, default=str)
        st.download_button(
            "Export scenarios (JSON)",
            data=json_str,
            file_name="eibo_scenarios.json",
            mime="application/json",
            use_container_width=True,
            key="btn_export_json",
        )
    with export_col2:
        csv_str = compare_df.to_csv(index=False)
        st.download_button(
            "Export comparison (CSV)",
            data=csv_str,
            file_name="eibo_scenarios.csv",
            mime="text/csv",
            use_container_width=True,
            key="btn_export_csv",
        )

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px 48px;'></div>",
        unsafe_allow_html=True,
    )
