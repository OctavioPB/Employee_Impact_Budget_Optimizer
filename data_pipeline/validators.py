"""Data quality validators for EIBO pipeline."""

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


REQUIRED_EMPLOYEE_COLS = {
    "employee_id", "full_name", "role_title", "department",
    "annual_salary", "hire_date", "team_id",
}

REQUIRED_TEAM_COLS = {
    "team_id", "team_name", "department", "annual_budget",
}

VALID_SENIORITY_LEVELS = {"junior", "mid", "senior", "lead", "director", "exec"}
SALARY_BOUNDS = (20_000, 2_000_000)
KPI_BOUNDS = (0.0, 5.0)


def validate_employee_dataframe(df: pd.DataFrame) -> ValidationResult:
    """Validate employee records against expected schema and business rules."""
    result = ValidationResult(is_valid=True)

    missing = REQUIRED_EMPLOYEE_COLS - set(df.columns)
    if missing:
        result.add_error(f"Missing required columns: {missing}")
        return result

    null_counts = df[list(REQUIRED_EMPLOYEE_COLS)].isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            result.add_error(f"Column '{col}' has {count} null values")

    if "employee_id" in df.columns and df["employee_id"].duplicated().any():
        n_dups = df["employee_id"].duplicated().sum()
        result.add_error(f"Found {n_dups} duplicate employee_id values")

    if "annual_salary" in df.columns:
        lo, hi = SALARY_BOUNDS
        out_of_range = df[(df["annual_salary"] < lo) | (df["annual_salary"] > hi)]
        if not out_of_range.empty:
            result.add_warning(
                f"{len(out_of_range)} employees have salary outside [{lo:,}, {hi:,}]"
            )

    if "seniority_level" in df.columns:
        invalid = set(df["seniority_level"].dropna().unique()) - VALID_SENIORITY_LEVELS
        if invalid:
            result.add_error(f"Invalid seniority_level values: {invalid}")

    return result


def validate_performance_dataframe(df: pd.DataFrame) -> ValidationResult:
    """Validate performance records."""
    result = ValidationResult(is_valid=True)

    required = {"performance_id", "employee_id", "review_date", "kpi_score"}
    missing = required - set(df.columns)
    if missing:
        result.add_error(f"Missing required columns: {missing}")
        return result

    if "kpi_score" in df.columns:
        lo, hi = KPI_BOUNDS
        bad = df[(df["kpi_score"] < lo) | (df["kpi_score"] > hi)]
        if not bad.empty:
            result.add_error(
                f"{len(bad)} performance records have kpi_score outside [{lo}, {hi}]"
            )

    return result


def validate_team_dataframe(df: pd.DataFrame) -> ValidationResult:
    """Validate team records."""
    result = ValidationResult(is_valid=True)

    missing = REQUIRED_TEAM_COLS - set(df.columns)
    if missing:
        result.add_error(f"Missing required columns: {missing}")
        return result

    if "annual_budget" in df.columns:
        negative = df[df["annual_budget"] < 0]
        if not negative.empty:
            result.add_error(f"{len(negative)} teams have negative annual_budget")

    return result


def validate_csv_columns(
    df: pd.DataFrame, required: set[str], source: str
) -> ValidationResult:
    """Generic column presence check for raw CSV ingestion."""
    result = ValidationResult(is_valid=True)
    missing = required - set(df.columns)
    if missing:
        result.add_error(f"[{source}] Missing columns: {missing}")
    return result
