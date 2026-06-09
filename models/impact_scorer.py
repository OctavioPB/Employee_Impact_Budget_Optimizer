"""Impact Scoring: 0-100 score combining KPI performance, network centrality, skills, and cost.

Scoring formula (per PLAN.md):
  impact_score = 0.40 × kpi_component
               + 0.30 × network_component
               + 0.20 × skills_component
               + 0.10 × cost_component
  (all components normalized [0, 1]; final score scaled to [0, 100])

Default mode: heuristic scoring — no training data required.
Optional mode: Random Forest trained on historical retention labels with SHAP explainability.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

_W_KPI = 0.40
_W_NETWORK = 0.30
_W_SKILLS = 0.20
_W_COST = 0.10

_KPI_MIN = 1.0
_KPI_MAX = 5.0

# Market salary multiplier for replacement cost: applied relative to department median
_MARKET_MULTIPLIER_BASE = 1.30


@dataclass
class ScoringResult:
    """Output of ImpactScorer.score()."""

    scores: pd.DataFrame
    """Columns: employee_id, impact_score, kpi_contribution, network_contribution,
    skills_contribution, cost_contribution, confidence."""

    feature_importance: dict[str, float]
    """Feature importance from RF model (empty dict for heuristic mode)."""

    cv_accuracy: float
    """Cross-validation accuracy of the underlying RF (0.0 for heuristic mode)."""

    mode: str
    """'heuristic' or 'random_forest'."""


class ImpactScorer:
    """Computes 0-100 impact scores with SHAP-like component attribution.

    Usage:
        scorer = ImpactScorer()
        result = scorer.score(employees_df, performance_df, centrality_df,
                              employee_skills_df, skills_df)
    """

    def __init__(self, random_state: int = 42) -> None:
        self._random_state = random_state
        self._model: RandomForestClassifier | None = None
        self._scaler = MinMaxScaler()
        self._feature_cols: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        employees_df: pd.DataFrame,
        performance_df: pd.DataFrame,
        centrality_df: pd.DataFrame,
        employee_skills_df: pd.DataFrame,
        skills_df: pd.DataFrame,
        retention_labels: pd.Series | None = None,
    ) -> ScoringResult:
        """Compute impact scores for all active employees.

        Args:
            employees_df: Active employees with columns employee_id, department,
                          team_id, annual_salary, seniority_level, hire_date.
            performance_df: KPI history with columns employee_id, kpi_score, review_date.
            centrality_df: Output of network_analysis.compute_centrality_metrics().
            employee_skills_df: employee_id, skill_id, proficiency, is_primary.
            skills_df: skill_id, is_critical, market_scarcity.
            retention_labels: Optional Series indexed by employee_id (1=retained, 0=not retained).

        Returns:
            ScoringResult with per-employee impact scores and component breakdown.
        """
        features = self._build_features(
            employees_df, performance_df, centrality_df, employee_skills_df, skills_df
        )

        if retention_labels is not None and len(retention_labels) >= 20:
            return self._score_with_rf(features, retention_labels)

        return self._score_heuristic(features)

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def _build_features(
        self,
        employees_df: pd.DataFrame,
        performance_df: pd.DataFrame,
        centrality_df: pd.DataFrame,
        employee_skills_df: pd.DataFrame,
        skills_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Build feature DataFrame; one row per active employee."""
        base = employees_df[
            ["employee_id", "department", "team_id", "annual_salary",
             "seniority_level", "hire_date"]
        ].copy()

        base = base.merge(
            self._kpi_features(performance_df),
            on="employee_id",
            how="left",
        )

        base = base.merge(
            centrality_df[["employee_id", "combined_centrality",
                            "betweenness_centrality", "degree_centrality"]],
            on="employee_id",
            how="left",
        )

        base = base.merge(
            self._skill_features(employee_skills_df, skills_df),
            on="employee_id",
            how="left",
        )

        # Fill missing values — employees with no performance history get neutral KPI
        # pd.to_numeric handles object-dtype columns produced by left-merging an empty DataFrame
        base["avg_kpi"] = pd.to_numeric(base["avg_kpi"], errors="coerce")
        kpi_median = base["avg_kpi"].median()
        base["avg_kpi"] = base["avg_kpi"].fillna(kpi_median if pd.notna(kpi_median) else 3.0)

        base["kpi_trend"] = pd.to_numeric(base["kpi_trend"], errors="coerce").fillna(0.0)
        base["recency_kpi"] = pd.to_numeric(base["recency_kpi"], errors="coerce").fillna(
            base["avg_kpi"]
        )
        base["combined_centrality"] = base["combined_centrality"].fillna(0.0)
        base["betweenness_centrality"] = base["betweenness_centrality"].fillna(0.0)
        base["degree_centrality"] = base["degree_centrality"].fillna(0.0)
        base["skill_criticality"] = base["skill_criticality"].fillna(0.0)
        base["knowledge_uniqueness"] = base["knowledge_uniqueness"].fillna(0.5)

        base["tenure_years"] = self._tenure_years(base["hire_date"])
        base["replacement_cost_norm"] = self._replacement_cost(base)

        return base

    def _kpi_features(self, performance_df: pd.DataFrame) -> pd.DataFrame:
        """Compute per-employee: avg_kpi, kpi_trend, recency_kpi."""
        if performance_df.empty:
            return pd.DataFrame(
                columns=["employee_id", "avg_kpi", "kpi_trend", "recency_kpi"]
            )

        df = performance_df.copy()
        df["review_date"] = pd.to_datetime(df["review_date"])
        df.sort_values(["employee_id", "review_date"], inplace=True)

        rows: list[dict] = []
        for emp_id, group in df.groupby("employee_id"):
            kpis = group["kpi_score"].to_numpy(dtype=float)
            n = len(kpis)
            avg_kpi = float(kpis.mean())

            # Recency-weighted average: exponential decay, most recent = highest weight
            weights = np.exp(np.linspace(-1, 0, n))
            recency_kpi = float(np.average(kpis, weights=weights))

            # KPI trend: linear regression slope over time (positive = improving)
            if n >= 2:
                x = np.arange(n, dtype=float)
                slope = float(np.polyfit(x, kpis, 1)[0])
            else:
                slope = 0.0

            rows.append({
                "employee_id": str(emp_id),
                "avg_kpi": round(avg_kpi, 4),
                "kpi_trend": round(slope, 4),
                "recency_kpi": round(recency_kpi, 4),
            })

        return pd.DataFrame(rows)

    def _skill_features(
        self, employee_skills_df: pd.DataFrame, skills_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Compute skill_criticality and knowledge_uniqueness per employee."""
        if employee_skills_df.empty or skills_df.empty:
            return pd.DataFrame(
                columns=["employee_id", "skill_criticality", "knowledge_uniqueness"]
            )

        merged = employee_skills_df.merge(
            skills_df[["skill_id", "is_critical", "market_scarcity"]],
            on="skill_id",
            how="left",
        )

        rows: list[dict] = []
        # Track skill → employee count for uniqueness calculation
        skill_holder_counts = (
            merged.groupby("skill_id")["employee_id"].nunique()
        ).to_dict()

        for emp_id, group in merged.groupby("employee_id"):
            critical = group[group["is_critical"]]
            if not critical.empty:
                skill_crit = float(
                    (critical["proficiency"] * critical["market_scarcity"]).mean()
                )
            else:
                skill_crit = 0.0

            # knowledge_uniqueness: inverse of avg holders for employee's critical skills
            # 1.0 = sole holder, 0.0 = common skills
            if not critical.empty:
                holder_counts = critical["skill_id"].map(skill_holder_counts).to_numpy(float)
                n_employees = employee_skills_df["employee_id"].nunique()
                # Normalize: 1 / (holders / total_employees) → inverted frequency
                uniqueness = float(np.mean(1.0 / np.maximum(holder_counts / n_employees, 0.01)))
                uniqueness = float(np.clip(uniqueness, 0.0, 1.0))
            else:
                uniqueness = 0.3  # no critical skills → moderate uniqueness

            rows.append({
                "employee_id": str(emp_id),
                "skill_criticality": round(skill_crit, 4),
                "knowledge_uniqueness": round(uniqueness, 4),
            })

        return pd.DataFrame(rows)

    @staticmethod
    def _tenure_years(hire_date_series: pd.Series) -> pd.Series:
        """Convert hire_date to tenure in years (float)."""
        today = pd.Timestamp.today().normalize()
        dates = pd.to_datetime(hire_date_series, errors="coerce")
        return ((today - dates).dt.days / 365.25).clip(lower=0).round(2)

    @staticmethod
    def _replacement_cost(features: pd.DataFrame) -> pd.Series:
        """Replacement cost factor relative to department median salary, normalized [0, 1]."""
        dept_median = features.groupby("department")["annual_salary"].transform("median")
        raw = (features["annual_salary"] / dept_median.replace(0, np.nan)).fillna(1.0)
        raw = raw * _MARKET_MULTIPLIER_BASE
        max_val = raw.max()
        return (raw / max_val if max_val > 0 else raw).round(4)

    # ------------------------------------------------------------------
    # Heuristic scoring
    # ------------------------------------------------------------------

    def _score_heuristic(self, features: pd.DataFrame) -> ScoringResult:
        """Apply the 40/30/20/10 weighted formula directly to normalized feature components."""
        kpi_raw = (
            (features["recency_kpi"] - _KPI_MIN) / (_KPI_MAX - _KPI_MIN)
        ).clip(0, 1)
        trend_raw = self._sigmoid(features["kpi_trend"] * 10)
        kpi_comp = (0.65 * kpi_raw + 0.35 * trend_raw).clip(0, 1)

        net_comp = features["combined_centrality"].clip(0, 1)

        skills_comp = (
            0.65 * features["skill_criticality"].clip(0, 1)
            + 0.35 * features["knowledge_uniqueness"].clip(0, 1)
        ).clip(0, 1)

        cost_comp = features["replacement_cost_norm"].clip(0, 1)

        impact = (
            _W_KPI * kpi_comp
            + _W_NETWORK * net_comp
            + _W_SKILLS * skills_comp
            + _W_COST * cost_comp
        ) * 100.0

        # Confidence: higher when employee has more data (performance reviews)
        confidence = self._compute_confidence(features)

        result_df = pd.DataFrame({
            "employee_id": features["employee_id"].values,
            "impact_score": impact.round(1).values,
            "kpi_contribution": (_W_KPI * kpi_comp * 100).round(2).values,
            "network_contribution": (_W_NETWORK * net_comp * 100).round(2).values,
            "skills_contribution": (_W_SKILLS * skills_comp * 100).round(2).values,
            "cost_contribution": (_W_COST * cost_comp * 100).round(2).values,
            "confidence": confidence.round(3).values,
        })

        logger.info(
            "Heuristic scoring: %d employees | mean=%.1f | range=[%.1f, %.1f]",
            len(result_df),
            result_df["impact_score"].mean(),
            result_df["impact_score"].min(),
            result_df["impact_score"].max(),
        )

        return ScoringResult(
            scores=result_df,
            feature_importance={},
            cv_accuracy=0.0,
            mode="heuristic",
        )

    # ------------------------------------------------------------------
    # Random Forest scoring (when historical labels are available)
    # ------------------------------------------------------------------

    def _score_with_rf(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
    ) -> ScoringResult:
        """Train RF on historical retention labels, then produce SHAP-style contributions."""
        self._feature_cols = [
            "recency_kpi", "kpi_trend", "avg_kpi",
            "combined_centrality", "betweenness_centrality",
            "skill_criticality", "knowledge_uniqueness",
            "replacement_cost_norm", "tenure_years",
        ]

        # Align labels with features
        label_df = labels.reset_index()
        label_df.columns = ["employee_id", "label"]
        merged = features.merge(label_df, on="employee_id", how="inner")

        X = merged[self._feature_cols].fillna(0.0).to_numpy()
        y = merged["label"].to_numpy()

        X_scaled = self._scaler.fit_transform(X)

        self._model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=5,
            random_state=self._random_state,
            n_jobs=-1,
        )
        self._model.fit(X_scaled, y)

        cv_scores = cross_val_score(
            RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                min_samples_leaf=5,
                random_state=self._random_state,
            ),
            X_scaled, y, cv=5, scoring="accuracy",
        )
        cv_acc = float(cv_scores.mean())

        feature_importance = dict(
            zip(self._feature_cols, self._model.feature_importances_.round(4), strict=False)
        )

        # Produce impact scores from RF retention probability → scaled to [0, 100]
        X_all = features[self._feature_cols].fillna(0.0).to_numpy()
        X_all_scaled = self._scaler.transform(X_all)
        proba = self._model.predict_proba(X_all_scaled)[:, 1]  # P(retained)

        # Component attribution: scale each feature's contribution by importance
        # This gives an approximate SHAP-like decomposition without importing shap
        importance_arr = self._model.feature_importances_
        X_norm = X_all_scaled  # already [0,1] after scaler
        contributions = X_norm * importance_arr  # shape: (n_employees, n_features)

        feat_idx = {f: i for i, f in enumerate(self._feature_cols)}

        kpi_cols = [feat_idx["recency_kpi"], feat_idx["kpi_trend"], feat_idx["avg_kpi"]]
        net_cols = [feat_idx["combined_centrality"], feat_idx["betweenness_centrality"]]
        skill_cols = [feat_idx["skill_criticality"], feat_idx["knowledge_uniqueness"]]
        cost_cols = [feat_idx["replacement_cost_norm"]]

        total_weight = contributions.sum(axis=1, keepdims=True)
        total_weight = np.where(total_weight == 0, 1.0, total_weight)
        contrib_pct = contributions / total_weight  # fractional contribution

        kpi_frac = contrib_pct[:, kpi_cols].sum(axis=1)
        net_frac = contrib_pct[:, net_cols].sum(axis=1)
        skill_frac = contrib_pct[:, skill_cols].sum(axis=1)
        cost_frac = contrib_pct[:, cost_cols].sum(axis=1)

        impact = proba * 100.0

        result_df = pd.DataFrame({
            "employee_id": features["employee_id"].values,
            "impact_score": impact.round(1),
            "kpi_contribution": (kpi_frac * impact).round(2),
            "network_contribution": (net_frac * impact).round(2),
            "skills_contribution": (skill_frac * impact).round(2),
            "cost_contribution": (cost_frac * impact).round(2),
            "confidence": np.full(len(features), round(cv_acc, 3)),
        })

        logger.info(
            "RF scoring: %d employees | cv_acc=%.3f | mean_score=%.1f",
            len(result_df), cv_acc, result_df["impact_score"].mean(),
        )

        return ScoringResult(
            scores=result_df,
            feature_importance=feature_importance,
            cv_accuracy=cv_acc,
            mode="random_forest",
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sigmoid(x: pd.Series) -> pd.Series:
        return 1.0 / (1.0 + np.exp(-x.clip(-20, 20)))

    @staticmethod
    def _compute_confidence(features: pd.DataFrame) -> pd.Series:
        """Confidence ∈ [0.4, 1.0]: higher when avg_kpi is not NaN and tenure >= 1yr."""
        base = pd.Series(0.6, index=features.index)
        has_kpi = features["avg_kpi"].notna() & (features["avg_kpi"] > 0)
        long_tenure = features["tenure_years"] >= 1.0
        base = base + has_kpi.astype(float) * 0.20 + long_tenure.astype(float) * 0.20
        return base.clip(0.4, 1.0)


def compute_impact_scores(
    employees_df: pd.DataFrame,
    performance_df: pd.DataFrame,
    centrality_df: pd.DataFrame,
    employee_skills_df: pd.DataFrame,
    skills_df: pd.DataFrame,
    retention_labels: pd.Series | None = None,
) -> ScoringResult:
    """Convenience function: instantiate ImpactScorer and return scores."""
    scorer = ImpactScorer()
    return scorer.score(
        employees_df=employees_df,
        performance_df=performance_df,
        centrality_df=centrality_df,
        employee_skills_df=employee_skills_df,
        skills_df=skills_df,
        retention_labels=retention_labels,
    )
