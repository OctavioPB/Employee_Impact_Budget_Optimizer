"""Attrition risk prediction model for EIBO.

Produces calibrated probability scores [0, 100] per employee with
additive feature attribution (SHAP-compatible structure).

Two operating modes:
  heuristic  — no training labels required; uses feature-based scoring.
               Safe for demo data where no historical attrition events exist.
  xgboost    — activated when ≥ 20 labeled records are provided.
               XGBoost + SMOTE + CalibratedClassifierCV (Platt scaling).
               SHAP TreeExplainer used for attribution.

Risk categories (per PLAN.md §5.1):
  Low Risk     (0–30)   : Stable
  Moderate Risk(31–60)  : Monitor
  High Risk    (61–80)  : Intervention Recommended
  Critical Risk(81–100) : Immediate Action Required
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

# Minimum labeled records required to activate XGBoost mode
_MIN_LABELS_FOR_XGB = 20

# Risk-category thresholds
_RISK_THRESHOLDS = [
    (81, "Critical Risk"),
    (61, "High Risk"),
    (31, "Moderate Risk"),
    (0,  "Low Risk"),
]

# Heuristic component weights (must sum to 1.0)
_W_SALARY     = 0.25   # low comp → higher risk
_W_KPI_TREND  = 0.25   # declining performance → higher risk
_W_TENURE     = 0.15   # very short or very long tenure → different risks
_W_NETWORK    = 0.15   # low centrality (isolation) → higher risk
_W_IMPACT     = 0.20   # low impact → higher risk (lower retention priority)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class AttritionResult:
    """Full output of AttritionPredictor."""

    scores: pd.DataFrame
    """Columns: employee_id, attrition_risk, risk_category,
    salary_driver, kpi_trend_driver, tenure_driver,
    network_driver, impact_driver, top_driver, confidence."""

    feature_importance: dict[str, float]
    """Global feature importance (empty in heuristic mode)."""

    model_auc: float
    """ROC-AUC from cross-validation (0.0 in heuristic mode)."""

    mode: str
    """'heuristic' or 'xgboost'."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_attrition_risk(
    employees_df: pd.DataFrame,
    performance_df: pd.DataFrame | None = None,
    centrality_df: pd.DataFrame | None = None,
    impact_scores_df: pd.DataFrame | None = None,
    attrition_labels: pd.DataFrame | None = None,
) -> AttritionResult:
    """Convenience wrapper around AttritionPredictor.

    Args:
        employees_df: Active employees with employee_id, annual_salary,
                      department, hire_date.
        performance_df: employee_id, kpi_score, review_date (historical).
        centrality_df: employee_id, combined_centrality.
        impact_scores_df: employee_id, impact_score.
        attrition_labels: Optional DataFrame with employee_id, left (0/1).

    Returns:
        AttritionResult with scores and attribution per employee.
    """
    predictor = AttritionPredictor()
    return predictor.predict(
        employees_df=employees_df,
        performance_df=performance_df,
        centrality_df=centrality_df,
        impact_scores_df=impact_scores_df,
        attrition_labels=attrition_labels,
    )


def risk_category(score: float) -> str:
    """Map a 0–100 risk score to its category label."""
    for threshold, label in _RISK_THRESHOLDS:
        if score >= threshold:
            return label
    return "Low Risk"


# ---------------------------------------------------------------------------
# Predictor class
# ---------------------------------------------------------------------------

class AttritionPredictor:
    """Two-mode attrition risk predictor."""

    def __init__(self) -> None:
        self._model = None
        self._scaler = MinMaxScaler()
        self._feature_names: list[str] = []
        self._mode: str = "heuristic"

    # ------------------------------------------------------------------
    # Main predict
    # ------------------------------------------------------------------

    def predict(
        self,
        employees_df: pd.DataFrame,
        performance_df: pd.DataFrame | None = None,
        centrality_df: pd.DataFrame | None = None,
        impact_scores_df: pd.DataFrame | None = None,
        attrition_labels: pd.DataFrame | None = None,
    ) -> AttritionResult:
        features = self._build_features(
            employees_df, performance_df, centrality_df, impact_scores_df
        )
        if features.empty:
            return self._empty_result()

        n_labels = 0
        if attrition_labels is not None and not attrition_labels.empty:
            n_labels = int(attrition_labels["left"].sum()) if "left" in attrition_labels else 0

        if n_labels >= _MIN_LABELS_FOR_XGB:
            return self._xgboost_predict(features, attrition_labels)
        return self._heuristic_predict(features, employees_df)

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def _build_features(
        self,
        employees_df: pd.DataFrame,
        performance_df: pd.DataFrame | None,
        centrality_df: pd.DataFrame | None,
        impact_scores_df: pd.DataFrame | None,
    ) -> pd.DataFrame:
        """Build the feature matrix aligned on employee_id."""
        if employees_df.empty:
            return pd.DataFrame()

        keep_cols = ["employee_id"]
        for col in ("department", "annual_salary", "hire_date"):
            if col in employees_df.columns:
                keep_cols.append(col)
        emp = employees_df[keep_cols].copy()

        # Ensure required columns exist with defaults
        if "department" not in emp.columns:
            emp["department"] = "Unknown"
        if "annual_salary" not in emp.columns:
            emp["annual_salary"] = 70_000.0
        if "hire_date" not in emp.columns:
            emp["hire_date"] = pd.NaT

        # Tenure in years
        today = pd.Timestamp.today().normalize()
        emp["tenure_years"] = (
            (today - pd.to_datetime(emp["hire_date"], errors="coerce")).dt.days / 365.25
        ).clip(lower=0).fillna(3.0)

        # Salary ratio vs market rate (preferred) or department median (fallback)
        if "market_salary" in employees_df.columns:
            mkt = employees_df["market_salary"].values.astype(float)
            emp["salary_ratio"] = (
                emp["annual_salary"].values / np.where(mkt > 0, mkt, np.nan)
            )
        else:
            dept_median = (
                emp.groupby("department")["annual_salary"]
                .transform("median")
                .fillna(emp["annual_salary"].median())
            )
            emp["salary_ratio"] = emp["annual_salary"] / dept_median.replace(0, np.nan)
        emp["salary_ratio"] = pd.to_numeric(
            emp["salary_ratio"], errors="coerce"
        ).fillna(1.0).clip(0.5, 2.0)

        # KPI features from performance history
        kpi_features = self._kpi_features(performance_df)
        emp = emp.merge(kpi_features, on="employee_id", how="left")
        emp["avg_kpi"]    = pd.to_numeric(emp.get("avg_kpi"), errors="coerce").fillna(3.0)
        emp["kpi_trend"]  = pd.to_numeric(emp.get("kpi_trend"), errors="coerce").fillna(0.0)

        # Network centrality
        _cent = centrality_df
        if _cent is not None and not _cent.empty and "combined_centrality" in _cent.columns:
            emp = emp.merge(
                _cent[["employee_id", "combined_centrality"]],
                on="employee_id", how="left"
            )
        else:
            emp["combined_centrality"] = 0.0
        emp["combined_centrality"] = pd.to_numeric(
            emp["combined_centrality"], errors="coerce"
        ).fillna(0.0)

        # Impact score
        _imp = impact_scores_df
        if _imp is not None and not _imp.empty and "impact_score" in _imp.columns:
            emp = emp.merge(
                _imp[["employee_id", "impact_score"]],
                on="employee_id", how="left"
            )
        else:
            emp["impact_score"] = 50.0
        emp["impact_score"] = pd.to_numeric(
            emp["impact_score"], errors="coerce"
        ).fillna(50.0)

        return emp.reset_index(drop=True)

    def _kpi_features(self, performance_df: pd.DataFrame | None) -> pd.DataFrame:
        """Compute avg_kpi and kpi_trend per employee from historical reviews."""
        if performance_df is None or performance_df.empty:
            return pd.DataFrame(columns=["employee_id", "avg_kpi", "kpi_trend"])

        perf = performance_df[["employee_id", "kpi_score", "review_date"]].copy()
        perf["kpi_score"]   = pd.to_numeric(perf["kpi_score"], errors="coerce")
        perf["review_date"] = pd.to_datetime(perf["review_date"], errors="coerce")
        perf = perf.dropna(subset=["kpi_score", "review_date"])

        if perf.empty:
            return pd.DataFrame(columns=["employee_id", "avg_kpi", "kpi_trend"])

        rows = []
        for emp_id, grp in perf.groupby("employee_id"):
            grp = grp.sort_values("review_date")
            scores = grp["kpi_score"].values
            # Recency-weighted average (recent = higher weight)
            n = len(scores)
            weights = np.exp(np.linspace(-1, 0, n))
            weights /= weights.sum()
            avg = float(np.dot(weights, scores))
            # Trend: slope of linear fit (positive = improving)
            trend = 0.0
            if n >= 2:
                x = np.arange(n, dtype=float)
                trend = float(np.polyfit(x, scores, 1)[0])
            rows.append({"employee_id": emp_id, "avg_kpi": avg, "kpi_trend": trend})

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Heuristic mode
    # ------------------------------------------------------------------

    def _heuristic_predict(
        self,
        features: pd.DataFrame,
        employees_df: pd.DataFrame,
    ) -> AttritionResult:
        """Score attrition risk from hand-crafted feature contributions.

        Each component is mapped to [0, 1] where 1 = maximum attrition risk.
        """
        df = features.copy()
        n = len(df)

        # --- salary driver: low ratio → high risk ---
        # salary_ratio in [0.5, 2.0]; risk peaks at ratio < 0.85
        sal = df["salary_ratio"].values
        salary_driver = np.clip(1.0 - (sal - 0.5) / 1.5, 0.0, 1.0)  # lower ratio → higher score

        # --- KPI trend driver: declining → high risk ---
        # kpi_trend is slope (could be positive or negative)
        kpi_trend = df["kpi_trend"].values
        max_abs = max(np.abs(kpi_trend).max(), 1e-6)
        kpi_trend_driver = np.clip(0.5 - kpi_trend / (2 * max_abs), 0.0, 1.0)

        # --- tenure driver: U-shaped (very short or very long = higher risk) ---
        tenure = df["tenure_years"].values
        # Peak risk at 0–1yr (onboarding) and after 7yr (stagnation)
        # Minimum risk around 3–5yr (engaged phase)
        tenure_driver = np.clip(
            1.0 - np.exp(-0.5 * ((tenure - 3.0) ** 2) / (2.5 ** 2)), 0.0, 1.0
        )

        # --- network driver: isolated employees leave more ---
        # combined_centrality in [0, 1]; low centrality → high risk
        net = df["combined_centrality"].values
        network_driver = np.clip(1.0 - net, 0.0, 1.0)

        # --- impact driver: low impact → higher risk proxy ---
        # Low-impact employees often feel undervalued or underutilized
        imp = df["impact_score"].values / 100.0
        impact_driver = np.clip(1.0 - imp * 0.8, 0.0, 1.0)

        # Weighted risk score [0, 100]
        raw = (
            _W_SALARY    * salary_driver +
            _W_KPI_TREND * kpi_trend_driver +
            _W_TENURE    * tenure_driver +
            _W_NETWORK   * network_driver +
            _W_IMPACT    * impact_driver
        )

        # Calibrate to realistic distribution: most employees are low-risk
        # Use sigmoid-like compression that keeps scores in 0-100
        calibrated = self._calibrate_heuristic(raw)

        # Confidence: higher when multiple features point in the same direction
        feature_std = np.std(
            np.column_stack([salary_driver, kpi_trend_driver,
                              tenure_driver, network_driver, impact_driver]),
            axis=1,
        )
        confidence = np.clip(0.5 + 0.5 * (1 - feature_std), 0.4, 0.95)

        top_driver = self._top_driver_labels(
            salary_driver, kpi_trend_driver, tenure_driver,
            network_driver, impact_driver,
        )

        scores_df = pd.DataFrame({
            "employee_id":    df["employee_id"],
            "attrition_risk": np.round(calibrated, 1),
            "risk_category":  [risk_category(s) for s in calibrated],
            "salary_driver":  np.round(salary_driver * 100, 1),
            "kpi_trend_driver": np.round(kpi_trend_driver * 100, 1),
            "tenure_driver":  np.round(tenure_driver * 100, 1),
            "network_driver": np.round(network_driver * 100, 1),
            "impact_driver":  np.round(impact_driver * 100, 1),
            "top_driver":     top_driver,
            "confidence":     np.round(confidence, 2),
        })

        logger.info(
            "Attrition heuristic: %d employees scored | avg_risk=%.1f | "
            "high+critical=%d",
            n,
            float(calibrated.mean()),
            int((calibrated >= 61).sum()),
        )
        return AttritionResult(
            scores=scores_df,
            feature_importance={
                "salary":    _W_SALARY,
                "kpi_trend": _W_KPI_TREND,
                "tenure":    _W_TENURE,
                "network":   _W_NETWORK,
                "impact":    _W_IMPACT,
            },
            model_auc=0.0,
            mode="heuristic",
        )

    def _calibrate_heuristic(self, raw: np.ndarray) -> np.ndarray:
        """Map raw [0, 1] scores to realistic [0, 100] attrition distribution.

        In practice attrition rate is ~15% annually. We push most scores below
        40 and reserve the 70+ range for genuinely at-risk patterns.
        """
        # Stretch via power transform then scale to [0, 100]
        stretched = np.power(raw, 1.4)
        return np.clip(stretched * 110, 0.0, 100.0)

    def _top_driver_labels(self, *drivers: np.ndarray) -> list[str]:
        names = ["Compensation", "Performance Trend", "Tenure", "Network Isolation", "Engagement"]
        result = []
        stacked = np.column_stack(drivers)
        for row in stacked:
            idx = int(np.argmax(row))
            result.append(names[idx])
        return result

    # ------------------------------------------------------------------
    # XGBoost mode
    # ------------------------------------------------------------------

    def _xgboost_predict(
        self,
        features: pd.DataFrame,
        attrition_labels: pd.DataFrame,
    ) -> AttritionResult:
        """Train XGBoost on labeled data, calibrate, return SHAP-attributed scores."""
        try:
            from xgboost import XGBClassifier
        except ImportError:
            logger.warning("xgboost not available; falling back to heuristic.")
            return self._heuristic_predict(features, features)

        feature_cols = ["salary_ratio", "avg_kpi", "kpi_trend",
                        "tenure_years", "combined_centrality", "impact_score"]
        self._feature_names = feature_cols

        # Merge labels
        labeled = features.merge(
            attrition_labels[["employee_id", "left"]],
            on="employee_id", how="inner",
        ).dropna(subset=["left"])

        if len(labeled) < _MIN_LABELS_FOR_XGB:
            logger.warning("Too few labels after merge; falling back to heuristic.")
            return self._heuristic_predict(features, features)

        X = labeled[feature_cols].fillna(0).values
        y = labeled["left"].astype(int).values

        # Class imbalance: use scale_pos_weight
        n_neg = int((y == 0).sum())
        n_pos = int((y == 1).sum())
        scale = n_neg / max(n_pos, 1)

        # Try SMOTE if available
        try:
            from imblearn.over_sampling import SMOTE
            sm = SMOTE(random_state=42, k_neighbors=min(5, n_pos - 1))
            X_res, y_res = sm.fit_resample(X, y)
        except Exception:
            X_res, y_res = X, y

        base = XGBClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.1,
            scale_pos_weight=scale,
            random_state=42,
            eval_metric="auc",
            verbosity=0,
        )
        calibrated = CalibratedClassifierCV(base, method="sigmoid", cv=3)

        # Cross-validation AUC
        cv = StratifiedKFold(n_splits=min(5, n_pos), shuffle=True, random_state=42)
        try:
            aucs = cross_val_score(calibrated, X_res, y_res, cv=cv, scoring="roc_auc")
            auc = float(aucs.mean())
        except Exception:
            auc = 0.0

        calibrated.fit(X_res, y_res)
        self._model = calibrated
        self._mode = "xgboost"

        # Predict on all employees
        X_all = features[feature_cols].fillna(0).values
        proba = calibrated.predict_proba(X_all)[:, 1]
        risk_scores = np.clip(proba * 100, 0, 100)

        # SHAP attribution (via base estimator before calibration)
        shap_drivers = self._shap_attribution(X_all, base, feature_cols, X_res, y_res)

        top_driver = [
            feature_cols[int(np.argmax(np.abs(row)))]
            .replace("_", " ").title()
            for row in shap_drivers
        ]

        feature_importance = dict(zip(
            feature_cols,
            np.abs(shap_drivers).mean(axis=0).round(4).tolist(), strict=False,
        ))

        scores_df = pd.DataFrame({
            "employee_id":    features["employee_id"],
            "attrition_risk": np.round(risk_scores, 1),
            "risk_category":  [risk_category(s) for s in risk_scores],
            "salary_driver":     np.round(np.abs(shap_drivers[:, 0]) * 100, 1),
            "kpi_trend_driver":  np.round(np.abs(shap_drivers[:, 2]) * 100, 1),
            "tenure_driver":     np.round(np.abs(shap_drivers[:, 3]) * 100, 1),
            "network_driver":    np.round(np.abs(shap_drivers[:, 4]) * 100, 1),
            "impact_driver":     np.round(np.abs(shap_drivers[:, 5]) * 100, 1),
            "top_driver":        top_driver,
            "confidence":        np.round(np.clip(proba * 0.6 + 0.4, 0.4, 0.95), 2),
        })

        logger.info(
            "Attrition XGBoost: %d employees | AUC=%.3f | "
            "high+critical=%d",
            len(features),
            auc,
            int((risk_scores >= 61).sum()),
        )
        return AttritionResult(
            scores=scores_df,
            feature_importance=feature_importance,
            model_auc=auc,
            mode="xgboost",
        )

    def _shap_attribution(
        self,
        X_all: np.ndarray,
        base_clf,
        feature_cols: list[str],
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> np.ndarray:
        """Compute SHAP values using TreeExplainer if available, else permutation."""
        try:
            import shap
            base_clf.fit(X_train, y_train)
            explainer = shap.TreeExplainer(base_clf)
            shap_values = explainer.shap_values(X_all)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
            return np.array(shap_values)
        except Exception as exc:
            logger.debug("SHAP TreeExplainer failed (%s); using permutation approximation.", exc)
            return self._permutation_attribution(X_all, base_clf, X_train, y_train)

    def _permutation_attribution(
        self,
        X_all: np.ndarray,
        clf,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> np.ndarray:
        """Fallback: estimate feature importance by column std × sign of gradient."""
        clf.fit(X_train, y_train)
        n_features = X_all.shape[1]
        baseline = clf.predict_proba(X_all)[:, 1]
        attribution = np.zeros_like(X_all, dtype=float)
        for j in range(n_features):
            X_perm = X_all.copy()
            X_perm[:, j] = X_all[:, j].mean()
            permuted = clf.predict_proba(X_perm)[:, 1]
            attribution[:, j] = baseline - permuted
        return attribution

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_result(self) -> AttritionResult:
        return AttritionResult(
            scores=pd.DataFrame(columns=[
                "employee_id", "attrition_risk", "risk_category",
                "salary_driver", "kpi_trend_driver", "tenure_driver",
                "network_driver", "impact_driver", "top_driver", "confidence",
            ]),
            feature_importance={},
            model_auc=0.0,
            mode="heuristic",
        )
