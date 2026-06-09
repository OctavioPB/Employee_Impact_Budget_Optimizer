"""Compensation Intelligence & Pay Equity Engine for EIBO.

Computes market benchmarking (comp_ratio), pay equity analysis with OLS-adjusted
gaps, and retention ROI for below-market employees.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
from scipy import stats

from backend.services.data_service import get_org
from demo_data.generator import _ROLE_SALARY

_SENIORITY_ORDER = {"junior": 0, "mid": 1, "senior": 2, "lead": 3, "director": 4, "exec": 5}


def _market_median(dept: str, seniority: str) -> float:
    dept_map = _ROLE_SALARY.get(dept, _ROLE_SALARY["default"])
    mean, _ = dept_map.get(seniority, dept_map.get("mid", (85_000, 10_000)))
    return float(mean)


def _market_tier(comp_ratio: float) -> str:
    if comp_ratio < 0.85:
        return "Below Market"
    if comp_ratio <= 1.15:
        return "At Market"
    return "Above Market"


def build_compensation_data(scenario: str, size: str) -> dict:
    org = get_org(scenario.upper(), size.lower())
    df = org.employees.copy()

    # ── Market benchmarking ────────────────────────────────────────────────
    df["market_median"] = df.apply(
        lambda r: _market_median(r["department"], r["seniority_level"]), axis=1
    )
    df["comp_ratio"]  = (df["annual_salary"] / df["market_median"]).round(3)
    df["market_tier"] = df["comp_ratio"].apply(_market_tier)

    # ── Demographic group assignment (cohort-rank proxy) ───────────────────
    # Within each (dept, seniority) cohort, rank employees by salary.
    # Top 50% of earners → "Group A", bottom 50% → "Group B".
    # Simulates a measurable pay disparity for equity analysis without real
    # demographic data, while keeping the demo legally neutral.
    df["_cohort_rank"] = df.groupby(["department", "seniority_level"])["annual_salary"].rank(pct=True)
    df["demographic_group"] = df["_cohort_rank"].apply(
        lambda r: "Group A" if r >= 0.5 else "Group B"
    )

    # ── Pay equity by department ───────────────────────────────────────────
    dept_equity: list[dict] = []
    for dept, grp in df.groupby("department"):
        a_sal = grp[grp["demographic_group"] == "Group A"]["annual_salary"]
        b_sal = grp[grp["demographic_group"] == "Group B"]["annual_salary"]
        if len(a_sal) < 2 or len(b_sal) < 2:
            continue

        med_a = float(a_sal.median())
        med_b = float(b_sal.median())
        raw_gap = (med_a - med_b) / med_a * 100 if med_a > 0 else 0.0

        # OLS-adjusted gap: residualise salary on seniority rank, then compare
        grp2 = grp.copy()
        grp2["sen_rank"] = grp2["seniority_level"].map(_SENIORITY_ORDER).fillna(2).astype(float)
        X = np.column_stack([grp2["sen_rank"].values, np.ones(len(grp2))])
        y = grp2["annual_salary"].values.astype(float)
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            grp2["residual"] = y - X @ coeffs
        except Exception:
            grp2["residual"] = 0.0

        res_a = float(grp2[grp2["demographic_group"] == "Group A"]["residual"].median())
        res_b = float(grp2[grp2["demographic_group"] == "Group B"]["residual"].median())
        base  = float(grp["market_median"].median())
        adj_gap = (res_a - res_b) / base * 100 if base > 0 else 0.0

        _, p_val = stats.ttest_ind(a_sal, b_sal, equal_var=False)

        dept_equity.append({
            "department":       dept,
            "headcount":        len(grp),
            "group_a_count":    int(len(a_sal)),
            "group_b_count":    int(len(b_sal)),
            "group_a_median":   round(med_a),
            "group_b_median":   round(med_b),
            "raw_gap_pct":      round(raw_gap, 1),
            "adjusted_gap_pct": round(adj_gap, 1),
            "p_value":          round(float(p_val), 3),
            "significant":      bool(p_val < 0.05),
        })

    dept_equity.sort(key=lambda x: abs(x["raw_gap_pct"]), reverse=True)

    # ── Retention ROI (employees meaningfully below market) ────────────────
    roi_rows: list[dict] = []
    for _, row in df[df["comp_ratio"] < 0.90].iterrows():
        salary   = float(row["annual_salary"])
        median   = float(row["market_median"])
        corr     = median - salary
        if corr <= 0:
            continue
        repl = salary * 0.5   # industry benchmark: ~50% of annual salary to replace
        roi  = repl / corr
        roi_rows.append({
            "employee_id":      str(row["employee_id"])[:8].upper(),
            "full_name":        row["full_name"],
            "department":       row["department"],
            "seniority_level":  row["seniority_level"],
            "role_title":       row["role_title"],
            "annual_salary":    int(salary),
            "market_median":    int(median),
            "comp_ratio":       float(row["comp_ratio"]),
            "correction_cost":  int(round(corr)),
            "replacement_cost": int(round(repl)),
            "roi":              round(roi, 2),
        })

    roi_rows.sort(key=lambda x: x["roi"], reverse=True)

    # ── Employee rows ──────────────────────────────────────────────────────
    emp_rows = [
        {
            "employee_id":       str(row["employee_id"])[:8].upper(),
            "full_name":         row["full_name"],
            "department":        row["department"],
            "seniority_level":   row["seniority_level"],
            "role_title":        row["role_title"],
            "annual_salary":     int(row["annual_salary"]),
            "market_median":     int(row["market_median"]),
            "comp_ratio":        float(row["comp_ratio"]),
            "market_tier":       row["market_tier"],
            "demographic_group": row["demographic_group"],
        }
        for _, row in df.iterrows()
    ]

    # ── Summary KPIs ───────────────────────────────────────────────────────
    n_total = len(df)
    n_below = int((df["market_tier"] == "Below Market").sum())
    n_above = int((df["market_tier"] == "Above Market").sum())
    avg_eq  = float(np.mean([r["raw_gap_pct"] for r in dept_equity])) if dept_equity else 0.0

    return {
        "summary": {
            "total_employees":    n_total,
            "median_comp_ratio":  round(float(df["comp_ratio"].median()), 3),
            "pct_below_market":   round(n_below / n_total * 100, 1),
            "pct_at_market":      round((n_total - n_below - n_above) / n_total * 100, 1),
            "pct_above_market":   round(n_above / n_total * 100, 1),
            "avg_equity_gap_pct": round(avg_eq, 1),
            "high_roi_candidates": len([r for r in roi_rows if r["roi"] >= 2.0]),
        },
        "employees":     emp_rows,
        "dept_equity":   dept_equity,
        "retention_roi": roi_rows,
    }
