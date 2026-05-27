"""
Sprint 20 — Real-Time Engagement Signal Ingestion & Pulse Monitoring.

Generates synthetic metadata-only engagement signals for all employees,
runs IsolationForest anomaly detection, CUSUM control chart alerting,
and builds the pulse monitoring dashboard data.

PRIVACY NOTE: In production, signal collection requires explicit employee
consent and a documented data processing agreement. It is disabled by
default in all deployments. All signals processed here are metadata
aggregates — no message content is ever accessed or stored.
"""

import hashlib
import sys
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.services.data_service import get_org

# ── Signal metadata ────────────────────────────────────────────────────────────

SIGNAL_META: list[dict] = [
    {
        "name":            "calendar_density_7d",
        "label":           "Meeting Density",
        "unit":            "meetings/day",
        "alert_direction": "both",
        "healthy_range":   "3 – 6",
        "mu":              4.5,
        "sigma":           1.5,
    },
    {
        "name":            "cross_team_interaction_7d",
        "label":           "Cross-Team Reach",
        "unit":            "contacts/day",
        "alert_direction": "low",
        "healthy_range":   "2 – 5",
        "mu":              3.0,
        "sigma":           1.2,
    },
    {
        "name":            "response_latency_trend",
        "label":           "Response Latency Trend",
        "unit":            "σ drift",
        "alert_direction": "high",
        "healthy_range":   "−0.5 to 0.5",
        "mu":              0.0,
        "sigma":           0.5,
    },
    {
        "name":            "pto_utilization_rate",
        "label":           "PTO Utilization",
        "unit":            "ratio 0–1",
        "alert_direction": "both",
        "healthy_range":   "0.3 – 0.7",
        "mu":              0.5,
        "sigma":           0.2,
    },
    {
        "name":            "after_hours_ratio",
        "label":           "After-Hours Activity",
        "unit":            "ratio 0–1",
        "alert_direction": "high",
        "healthy_range":   "< 0.15",
        "mu":              0.12,
        "sigma":           0.08,
    },
    {
        "name":            "collaboration_network_delta",
        "label":           "Network Size Delta",
        "unit":            "σ drift",
        "alert_direction": "low",
        "healthy_range":   "−0.3 to 0.3",
        "mu":              0.0,
        "sigma":           0.3,
    },
]

SIGNAL_NAMES = [s["name"] for s in SIGNAL_META]
ALERT_DIRECTIONS = [s["alert_direction"] for s in SIGNAL_META]
N_SIGNALS = len(SIGNAL_NAMES)
N_DAYS = 90
N_BASELINE = 70  # first 70 days used as baseline for CUSUM
_CLIP_BOUNDS = [(0, 15), (0, 15), (-2, 3), (0, 1), (0, 1), (-2, 1)]

# ── Score helpers ──────────────────────────────────────────────────────────────

def _add_scores(df: pd.DataFrame) -> pd.DataFrame:
    rng      = np.random.default_rng(42)
    sal_rank = df["annual_salary"].rank(pct=True)
    nexus_b  = df["_is_nexus"].astype(float) * 15
    noise    = rng.normal(0, 5, len(df))
    df       = df.copy()
    df["impact_score"]   = np.clip(sal_rank * 70 + nexus_b + noise, 0, 100).round(1)
    sal_inv  = 1 - sal_rank
    nexus_r  = df["_is_nexus"].astype(float) * 0.15
    attr_raw = sal_inv * 0.6 + rng.uniform(0, 0.4, len(df)) - nexus_r
    df["attrition_risk"] = np.clip(attr_raw, 0.01, 0.99).round(3)
    return df


def _anon_id(employee_id: str, role: str) -> str:
    h = hashlib.md5(employee_id.encode()).hexdigest()[:5].upper()
    role_short = role.split()[0] if role else "EMP"
    return f"[{role_short}-{h}]"


# ── Signal generation ──────────────────────────────────────────────────────────

def _generate_signal_series(df: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """
    Returns ndarray of shape (N_DAYS, n_employees, N_SIGNALS).
    Day 0 = 90 days ago, Day N_DAYS-1 = yesterday.
    """
    n = len(df)
    attrition = df["attrition_risk"].values       # (n,)
    nexus     = df["_is_nexus"].astype(float).values  # (n,)

    # Base signal level per employee (shape: n × N_SIGNALS)
    base = np.column_stack([
        np.clip(4.5 - attrition * 2.0 + nexus * 2.0, 0.5, 12),   # calendar_density_7d
        np.clip(3.0 - attrition * 1.5 + nexus * 1.5, 0.3, 12),   # cross_team_interaction_7d
        np.clip(attrition * 1.5,             0.0, 2.5),            # response_latency_trend
        np.clip(0.3 + attrition * 0.4,       0.0, 1.0),            # pto_utilization_rate
        np.clip(0.05 + attrition * 0.3,      0.0, 0.9),            # after_hours_ratio
        np.clip(-attrition * 0.8,            -1.8, 0.3),           # collaboration_network_delta
    ])  # (n, N_SIGNALS)

    # Per-signal noise scales
    noise_scales = np.array([0.25, 0.18, 0.12, 0.04, 0.02, 0.07])

    # Random walk noise: (N_DAYS, n, N_SIGNALS)
    increments = rng.normal(0, 1, (N_DAYS, n, N_SIGNALS)) * noise_scales
    walk       = np.cumsum(increments * 0.08, axis=0)  # damped random walk

    # Drift in last 14 days toward anomalous direction for high-risk employees
    # drift direction per signal: calendar↓, cross-team↓, latency↑, pto↑, after-hours↑, network↓
    drift_dir = np.array([-0.04, -0.03,  0.05,  0.008,  0.008, -0.025])
    for d in range(76, N_DAYS):
        strength   = attrition * (d - 75) / 14.0  # ramps up over 14 days
        walk[d] += strength[:, np.newaxis] * drift_dir  # (n, N_SIGNALS)

    series = base[np.newaxis, :, :] + walk  # (N_DAYS, n, N_SIGNALS)

    # Clip to valid ranges
    for j, (lo, hi) in enumerate(_CLIP_BOUNDS):
        series[:, :, j] = np.clip(series[:, :, j], lo, hi)

    return series.round(4)


# ── Anomaly detection ──────────────────────────────────────────────────────────

def _isolation_forest_scores(last_day: np.ndarray) -> np.ndarray:
    """
    last_day: (n_employees, N_SIGNALS) — signal values on the most recent day.
    Returns anomaly_score: (n_employees,) in [0, 1]. Higher = more anomalous.
    """
    clf    = IsolationForest(contamination=0.10, random_state=42, n_estimators=100)
    clf.fit(last_day)
    raw    = clf.decision_function(last_day)   # higher = more normal
    lo, hi = raw.min(), raw.max()
    span   = hi - lo if hi > lo else 1.0
    return ((hi - raw) / span).clip(0, 1)     # invert → higher = more anomalous


def _cusum_alerts(series: np.ndarray, k: float = 0.5, h: float = 3.0) -> np.ndarray:
    """
    series: (N_DAYS, n_employees, N_SIGNALS)
    Returns bool array (n_employees, N_SIGNALS) — True if CUSUM triggered.
    """
    baseline    = series[:N_BASELINE]
    mu          = baseline.mean(axis=0)                # (n, N_SIGNALS)
    sigma       = baseline.std(axis=0) + 1e-9

    recent = (series[N_BASELINE:] - mu[np.newaxis]) / sigma[np.newaxis]

    S_up  = np.zeros(mu.shape)
    S_dn  = np.zeros(mu.shape)
    alert_up = np.zeros(mu.shape, dtype=bool)
    alert_dn = np.zeros(mu.shape, dtype=bool)

    for day_vals in recent:
        S_up  = np.maximum(0, S_up + day_vals - k)
        S_dn  = np.maximum(0, S_dn - day_vals - k)
        alert_up |= S_up > h
        alert_dn |= S_dn > h

    alerts = np.zeros(mu.shape, dtype=bool)
    for j, direction in enumerate(ALERT_DIRECTIONS):
        if direction == "high":
            alerts[:, j] = alert_up[:, j]
        elif direction == "low":
            alerts[:, j] = alert_dn[:, j]
        else:
            alerts[:, j] = alert_up[:, j] | alert_dn[:, j]

    return alerts   # (n_employees, N_SIGNALS)


# ── Dashboard components ───────────────────────────────────────────────────────

def _build_heatmap(df: pd.DataFrame, last_day: np.ndarray) -> list[dict]:
    """Department × signal z-score grid."""
    org_mu    = last_day.mean(axis=0)     # (N_SIGNALS,)
    org_sigma = last_day.std(axis=0) + 1e-9

    rows = []
    for dept, grp in df.groupby("department"):
        idx        = grp.index.tolist()
        dept_vals  = last_day[idx].mean(axis=0)  # (N_SIGNALS,)
        zscores    = (dept_vals - org_mu) / org_sigma

        signals: dict[str, dict] = {}
        for j, meta in enumerate(SIGNAL_META):
            z     = float(zscores[j].round(2))
            v     = float(dept_vals[j].round(3))
            # alert if |z| > 1.5 in the concerning direction
            direction = meta["alert_direction"]
            if direction == "high":
                alert = z > 1.5
            elif direction == "low":
                alert = z < -1.5
            else:
                alert = abs(z) > 1.5
            signals[meta["name"]] = {"value": v, "zscore": z, "alert": alert}

        rows.append({
            "department": dept,
            "headcount":  len(grp),
            "signals":    signals,
        })

    return sorted(rows, key=lambda r: r["department"])


def _build_early_warning(
    df: pd.DataFrame,
    series: np.ndarray,
    anomaly_scores: np.ndarray,
    cusum_alerts: np.ndarray,
    top_n: int = 15,
) -> list[dict]:
    """Top employees by anomaly score with signal z-scores and adjusted risk."""
    last_day    = series[-1]   # (n, N_SIGNALS)
    baseline_mu = series[:N_BASELINE].mean(axis=0)
    baseline_sd = series[:N_BASELINE].std(axis=0) + 1e-9
    last_z      = (last_day - baseline_mu) / baseline_sd  # per-employee z vs own baseline

    top_idx = np.argsort(anomaly_scores)[::-1][:top_n]
    result  = []

    for i in top_idx:
        row          = df.iloc[i]
        base_risk    = float(row["attrition_risk"])
        adjusted     = float(np.clip(base_risk + anomaly_scores[i] * 0.30, 0, 1))
        cusum_flagged = [SIGNAL_NAMES[j] for j in range(N_SIGNALS) if cusum_alerts[i, j]]

        result.append({
            "employee_id":            row["employee_id"],
            "anon_id":                _anon_id(row["employee_id"], row["role_title"]),
            "role_title":             row["role_title"],
            "department":             row["department"],
            "seniority_level":        row["seniority_level"],
            "is_nexus":               bool(row["_is_nexus"]),
            "anomaly_score":          round(float(anomaly_scores[i]), 3),
            "base_attrition_risk":    round(base_risk, 3),
            "adjusted_attrition_risk":round(adjusted, 3),
            "cusum_alerts":           cusum_flagged,
            "signal_zscores":         {
                SIGNAL_NAMES[j]: round(float(last_z[i, j]), 2)
                for j in range(N_SIGNALS)
            },
        })

    return result


def _build_timelines(
    df: pd.DataFrame,
    series: np.ndarray,
    anomaly_scores: np.ndarray,
    top_n: int = 15,
) -> list[dict]:
    """90-day signal timelines for the top-N most anomalous employees."""
    top_idx = np.argsort(anomaly_scores)[::-1][:top_n]
    result  = []

    for i in top_idx:
        row = df.iloc[i]
        result.append({
            "employee_id": row["employee_id"],
            "anon_id":     _anon_id(row["employee_id"], row["role_title"]),
            "role_title":  row["role_title"],
            "department":  row["department"],
            "signals": {
                SIGNAL_NAMES[j]: series[:, i, j].round(3).tolist()
                for j in range(N_SIGNALS)
            },
        })

    return result


def _build_team_cohesion(df: pd.DataFrame, series: np.ndarray) -> list[dict]:
    """
    Per-department collaboration cohesion using cross_team_interaction_7d (signal index 1).
    Returns 30-day trend + cohesion score (0-100).
    """
    signal_idx = 1  # cross_team_interaction_7d
    cohesion_series = series[:, :, signal_idx]  # (N_DAYS, n_employees)
    trend_start     = N_DAYS - 30

    result = []
    for dept, grp in df.groupby("department"):
        idx          = grp.index.tolist()
        dept_series  = cohesion_series[:, idx]          # (N_DAYS, dept_size)
        dept_mean    = dept_series.mean(axis=1)          # (N_DAYS,)

        trend        = dept_mean[trend_start:].tolist()  # last 30 days
        cohesion_now = float(dept_mean[-1])
        delta_30d    = float(dept_mean[-1] - dept_mean[trend_start])

        # Cohesion score: normalize cross-team interaction to 0-100
        # Healthy ~3 contacts/day → 70 score; >5 → ~100; <1 → ~20
        cohesion_score = float(np.clip((cohesion_now / 5.0) * 100, 0, 100))

        result.append({
            "department":    dept,
            "headcount":     len(grp),
            "cohesion_score":round(cohesion_score, 1),
            "trend":         [round(v, 3) for v in trend],
            "delta_30d":     round(delta_30d, 3),
        })

    return sorted(result, key=lambda r: r["cohesion_score"])


# ── Main entry ─────────────────────────────────────────────────────────────────

def build_pulse_data(scenario: str, size: str) -> dict:
    df  = get_org(scenario.upper(), size.lower()).employees
    df  = _add_scores(df).reset_index(drop=True)

    rng = np.random.default_rng(77)  # different seed from other services
    series = _generate_signal_series(df, rng)   # (N_DAYS, n, N_SIGNALS)

    last_day       = series[-1]                  # (n, N_SIGNALS)
    anomaly_scores = _isolation_forest_scores(last_day)
    cusum_flags    = _cusum_alerts(series)

    anomaly_count  = int((anomaly_scores > 0.65).sum())
    cusum_count    = int(cusum_flags.any(axis=1).sum())

    today = date.today().isoformat()

    return {
        "enabled":    True,
        "disclaimer": (
            "DEMO MODE — All signals are synthetic metadata. In production, "
            "signal collection requires explicit employee consent and a documented "
            "data processing agreement. This feature is disabled by default."
        ),
        "summary": {
            "headcount":          len(df),
            "monitored":          len(df),
            "anomaly_count":      anomaly_count,
            "cusum_alert_count":  cusum_count,
            "avg_anomaly_score":  round(float(anomaly_scores.mean()), 3),
            "collection_date":    today,
        },
        "signal_definitions": SIGNAL_META,
        "heatmap":             _build_heatmap(df, last_day),
        "early_warning":       _build_early_warning(df, series, anomaly_scores, cusum_flags),
        "timelines":           _build_timelines(df, series, anomaly_scores),
        "team_cohesion":       _build_team_cohesion(df, series),
    }
