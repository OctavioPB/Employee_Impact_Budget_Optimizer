"""Internal Talent Mobility & Career Path Intelligence — Sprint 12.

Computes:
  - Career path suggestions per employee (skill-proximity based)
  - Career stagnation detection (tenure, KPI trend, salary percentile)
  - Succession depth mapping for leadership roles
"""

import sys
import math
from pathlib import Path
from datetime import date

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd

from demo_data.generator import _ROLE_BY_DEPT_SENIORITY, _DEPT_SKILLS, _ROLE_SALARY
from backend.services.data_service import get_org

# ── Seniority ordering ─────────────────────────────────────────────────────
_SEN_RANK = {"junior": 0, "mid": 1, "senior": 2, "lead": 3, "director": 4, "exec": 5}
_SEN_LEVELS = list(_SEN_RANK.keys())

# Cost to close each skill gap (professional upskilling, industry estimate)
_COST_PER_SKILL = 4_000

# ── Role catalog ────────────────────────────────────────────────────────────
# All (dept, seniority, role_title, skill_set, market_salary) combinations
_ROLE_CATALOG: list[dict] = []
for _dept, _by_sen in _ROLE_BY_DEPT_SENIORITY.items():
    _dept_skills = set(_DEPT_SKILLS.get(_dept, []))
    _sal_table   = _ROLE_SALARY.get(_dept, _ROLE_SALARY["default"])
    for _sen, _title in _by_sen.items():
        _mean_sal, _ = _sal_table.get(_sen, (85_000, 10_000))
        _ROLE_CATALOG.append({
            "dept":        _dept,
            "seniority":   _sen,
            "role_title":  _title,
            "skills":      _dept_skills,
            "market_salary": int(_mean_sal),
        })


def _jaccard_overlap(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _kpi_trend(perf_rows: pd.DataFrame) -> float:
    """Return per-quarter KPI slope via linear regression. Positive = improving."""
    if len(perf_rows) < 3:
        return 0.0
    scores = perf_rows.sort_values("review_date")["kpi_score"].values
    x = np.arange(len(scores), dtype=float)
    if x.std() == 0:
        return 0.0
    return float(np.polyfit(x, scores, 1)[0])


def build_mobility_data(scenario: str, size: str) -> dict:
    org     = get_org(scenario.upper(), size.lower())
    emp_df  = org.employees.copy().reset_index(drop=True)
    perf_df = org.performance.copy()
    emp_skills_df = org.employee_skills.copy()
    skills_df     = org.skills.copy()

    today = date.today()

    # ── Lookups ────────────────────────────────────────────────────────────
    skill_id_to_name: dict[str, str] = dict(
        zip(skills_df["skill_id"].astype(str), skills_df["skill_name"])
    )

    # employee_id → set of skill names
    emp_skill_map: dict[str, set] = {}
    for _, row in emp_skills_df.iterrows():
        eid = str(row["employee_id"])
        sn  = skill_id_to_name.get(str(row["skill_id"]), "")
        if sn:
            emp_skill_map.setdefault(eid, set()).add(sn)

    # employee_id → list of kpi records
    perf_by_emp: dict[str, pd.DataFrame] = {
        eid: grp for eid, grp in perf_df.groupby("employee_id")
    }

    # ── Salary percentile within (dept, seniority) cohort ─────────────────
    emp_df["sal_pct_in_cohort"] = emp_df.groupby(["department", "seniority_level"])[
        "annual_salary"
    ].rank(pct=True)

    # ── Stagnation scores ──────────────────────────────────────────────────
    stag_scores: list[float] = []
    kpi_trends:  list[float] = []

    for _, row in emp_df.iterrows():
        eid      = str(row["employee_id"])
        tenure   = (today - date.fromisoformat(str(row["hire_date"]))).days
        sal_pct  = float(row["sal_pct_in_cohort"])
        sen_rank = _SEN_RANK.get(str(row["seniority_level"]), 2)

        # Tenure signal (max 35)
        if tenure > 365 * 5:
            ten_sig = 35
        elif tenure > 365 * 3:
            ten_sig = 25
        elif tenure > 365 * 2:
            ten_sig = 15
        else:
            ten_sig = 0

        # Salary-in-cohort signal (max 25): bottom quartile = stagnant pay
        sal_sig = max(0, (0.30 - sal_pct) / 0.30 * 25) if sal_pct < 0.30 else 0

        # KPI trend signal (max 25): declining KPI over time
        perf_rows = perf_by_emp.get(eid, pd.DataFrame())
        trend = _kpi_trend(perf_rows)
        kpi_trends.append(float(trend))
        kpi_sig = max(0, min(-trend * 40, 25)) if trend < 0 else 0

        # Seniority-tenure mismatch (max 15): junior/mid with long tenure
        mismatch_sig = 15 if (sen_rank <= 1 and tenure > 365 * 3) else 0

        raw = ten_sig + sal_sig + kpi_sig + mismatch_sig
        stag_scores.append(min(float(raw), 100.0))

    emp_df["stagnation_score"] = [round(s, 1) for s in stag_scores]
    emp_df["kpi_trend"]        = [round(t, 4) for t in kpi_trends]

    # ── Career path suggestions ────────────────────────────────────────────
    career_paths: list[dict] = []
    max_suggestions = 3

    for _, row in emp_df.iterrows():
        eid      = str(row["employee_id"])
        emp_dept = str(row["department"])
        emp_sen  = str(row["seniority_level"])
        emp_rank = _SEN_RANK.get(emp_sen, 2)
        emp_skls = emp_skill_map.get(eid, set())
        curr_sal = float(row["annual_salary"])
        curr_title = str(row["role_title"])

        suggestions: list[dict] = []

        for role in _ROLE_CATALOG:
            tgt_rank = _SEN_RANK.get(role["seniority"], 2)

            # Only consider: same/next seniority level, not current role
            if role["role_title"] == curr_title:
                continue
            if tgt_rank < emp_rank:
                continue  # no demotions
            if tgt_rank > emp_rank + 1:
                continue  # max one step up

            role_skls = role["skills"]
            overlap   = _jaccard_overlap(emp_skls, role_skls)
            if overlap < 0.10:
                continue

            gap_skills     = sorted(role_skls - emp_skls)
            training_cost  = len(gap_skills) * _COST_PER_SKILL
            timeline_months = max(1, round(len(gap_skills) * 1.5))
            salary_uplift  = max(0, role["market_salary"] - curr_sal)
            roi = round(salary_uplift / training_cost, 2) if training_cost > 0 else 99.0
            score = overlap * salary_uplift / max(training_cost, 1)

            suggestions.append({
                "role_title":      role["role_title"],
                "department":      role["dept"],
                "seniority":       role["seniority"],
                "skill_overlap":   round(float(overlap), 3),
                "gap_skills":      gap_skills[:5],
                "training_cost":   int(training_cost),
                "timeline_months": int(timeline_months),
                "target_salary":   int(role["market_salary"]),
                "salary_uplift":   int(salary_uplift),
                "roi":             float(roi),
                "_score":          float(score),
            })

        suggestions.sort(key=lambda x: -x["_score"])
        top = []
        for s in suggestions[:max_suggestions]:
            s.pop("_score")
            top.append(s)

        career_paths.append({
            "employee_id":      str(row["employee_id"])[:8].upper(),
            "full_name":        str(row["full_name"]),
            "department":       emp_dept,
            "seniority_level":  emp_sen,
            "role_title":       curr_title,
            "annual_salary":    int(curr_sal),
            "stagnation_score": float(row["stagnation_score"]),
            "current_skills":   sorted(emp_skls),
            "suggestions":      top,
        })

    career_paths.sort(key=lambda x: -x["stagnation_score"])

    # ── Stagnation aggregation ─────────────────────────────────────────────
    # Dept × seniority heatmap
    stag_agg = emp_df.groupby(["department", "seniority_level"])["stagnation_score"].agg(
        ["mean", "count"]
    ).reset_index()
    stag_agg.columns = pd.Index(["department", "seniority_level", "avg_score", "count"])

    dept_seniority_heat: list[dict] = []
    for _, r in stag_agg.iterrows():
        dept_seniority_heat.append({
            "department":      str(r["department"]),
            "seniority_level": str(r["seniority_level"]),
            "avg_score":       round(float(r["avg_score"]), 1),
            "count":           int(r["count"]),
        })

    # Dept summary
    dept_stag = emp_df.groupby("department")["stagnation_score"].agg(["mean", "count"]).reset_index()
    dept_stag.columns = pd.Index(["department", "avg_score", "count"])
    dept_summary = [
        {
            "department": str(r["department"]),
            "avg_score":  round(float(r["avg_score"]), 1),
            "count":      int(r["count"]),
        }
        for _, r in dept_stag.sort_values("avg_score", ascending=False).iterrows()
    ]

    # High-risk stagnation employees (score ≥ 60)
    high_stag = emp_df[emp_df["stagnation_score"] >= 60].copy()
    high_stag = high_stag.sort_values("stagnation_score", ascending=False)
    high_stag_rows = [
        {
            "employee_id":      str(r["employee_id"])[:8].upper(),
            "full_name":        str(r["full_name"]),
            "department":       str(r["department"]),
            "seniority_level":  str(r["seniority_level"]),
            "role_title":       str(r["role_title"]),
            "tenure_days":      int((today - date.fromisoformat(str(r["hire_date"]))).days),
            "stagnation_score": float(r["stagnation_score"]),
            "annual_salary":    int(r["annual_salary"]),
        }
        for _, r in high_stag.iterrows()
    ]

    # ── Succession depth map ───────────────────────────────────────────────
    leadership_ranks = {"lead", "director", "exec"}
    leaders = emp_df[emp_df["seniority_level"].isin(leadership_ranks)].copy()

    succession_rows: list[dict] = []

    for _, leader in leaders.iterrows():
        l_dept = str(leader["department"])
        l_sen  = str(leader["seniority_level"])
        l_rank = _SEN_RANK.get(l_sen, 3)

        # Depth 1: same dept, one level below, stagnation < 50
        depth_1 = emp_df[
            (emp_df["department"] == l_dept) &
            (emp_df["seniority_level"].map(_SEN_RANK) == l_rank - 1) &
            (emp_df["stagnation_score"] < 50) &
            (emp_df["employee_id"] != leader["employee_id"])
        ]["full_name"].tolist()

        # Depth 2: same dept two levels below OR adjacent dept one level below
        depth_2_same = emp_df[
            (emp_df["department"] == l_dept) &
            (emp_df["seniority_level"].map(_SEN_RANK) == l_rank - 2) &
            (emp_df["employee_id"] != leader["employee_id"])
        ]["full_name"].tolist()

        depth_2 = (depth_2_same)[:5]

        # Depth 3: same dept, broader pool (3+ levels below)
        depth_3 = emp_df[
            (emp_df["department"] == l_dept) &
            (emp_df["seniority_level"].map(_SEN_RANK) <= l_rank - 3) &
            (emp_df["employee_id"] != leader["employee_id"])
        ]["full_name"].tolist()[:5]

        succession_rows.append({
            "employee_id":   str(leader["employee_id"])[:8].upper(),
            "leader_name":   str(leader["full_name"]),
            "role_title":    str(leader["role_title"]),
            "department":    l_dept,
            "seniority_level": l_sen,
            "depth_1":       depth_1[:5],
            "depth_2":       depth_2,
            "depth_3":       depth_3,
            "depth_1_count": len(depth_1),
            "depth_2_count": len(depth_2),
            "depth_3_count": len(depth_3),
            "succession_gap": len(depth_1) == 0,
        })

    # Sort: gaps first, then by seniority rank desc
    succession_rows.sort(key=lambda x: (-int(x["succession_gap"]), -_SEN_RANK.get(x["seniority_level"], 0)))

    # Limit to top 30 leaders for UI
    succession_rows = succession_rows[:30]

    # ── Summary ────────────────────────────────────────────────────────────
    n_total     = len(emp_df)
    n_stagnated = int((emp_df["stagnation_score"] >= 60).sum())
    avg_stag    = round(float(emp_df["stagnation_score"].mean()), 1)
    n_gaps      = sum(1 for s in succession_rows if s["succession_gap"])
    n_with_paths = sum(1 for cp in career_paths if len(cp["suggestions"]) > 0)

    return {
        "summary": {
            "total_employees":    n_total,
            "stagnated_count":    n_stagnated,
            "avg_stagnation":     avg_stag,
            "career_paths_count": n_with_paths,
            "succession_gaps":    n_gaps,
            "leaders_mapped":     len(succession_rows),
        },
        "career_paths":        career_paths,
        "stagnation": {
            "dept_summary":        dept_summary,
            "dept_seniority_heat": dept_seniority_heat,
            "high_risk":           high_stag_rows,
        },
        "succession": succession_rows,
    }
