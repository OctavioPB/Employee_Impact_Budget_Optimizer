"""Silver layer: data cleansing, normalization, and quality enforcement."""

import logging
import os

import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv

from data_pipeline.bronze_ingest import get_engine
from data_pipeline.validators import (
    validate_employee_dataframe,
    validate_performance_dataframe,
    validate_team_dataframe,
)

load_dotenv()
logger = logging.getLogger(__name__)


def _load_table(engine: sa.Engine, table: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_table(table, conn)


def cleanse_employees(engine: sa.Engine) -> pd.DataFrame:
    """
    Apply silver-layer cleansing to dim_employee.

    - Normalise salary to USD (already assumed USD for now)
    - Standardise seniority_level values
    - Enforce hire_date as date
    - Remove clearly invalid records (negative salary)
    """
    df = _load_table(engine, "dim_employee")

    seniority_map = {
        "intern": "junior", "associate": "junior",
        "staff": "mid", "principal": "senior",
        "manager": "lead", "sr manager": "lead",
        "vp": "director", "svp": "director", "evp": "exec",
        "c-level": "exec", "ceo": "exec", "cto": "exec", "coo": "exec",
    }
    df["seniority_level"] = (
        df["seniority_level"]
        .str.lower()
        .str.strip()
        .map(lambda v: seniority_map.get(v, v))
    )

    df["hire_date"] = pd.to_datetime(df["hire_date"], errors="coerce").dt.date
    df["annual_salary"] = pd.to_numeric(df["annual_salary"], errors="coerce")
    df["annual_benefits"] = pd.to_numeric(df["annual_benefits"], errors="coerce")

    # Impute missing benefits at 30% of salary
    mask = df["annual_benefits"].isna()
    df.loc[mask, "annual_benefits"] = df.loc[mask, "annual_salary"] * 0.30

    # Drop records with invalid core fields
    before = len(df)
    df = df[df["annual_salary"] > 0].copy()
    df = df.dropna(subset=["employee_id", "full_name", "hire_date"])
    removed = before - len(df)
    if removed:
        logger.warning("Dropped %d employee records during silver cleansing", removed)

    result = validate_employee_dataframe(df)
    for err in result.errors:
        logger.error("Silver validation error: %s", err)
    for warn in result.warnings:
        logger.warning("Silver validation warning: %s", warn)

    logger.info("Silver cleansing: %d clean employee records", len(df))
    return df


def cleanse_performance(engine: sa.Engine) -> pd.DataFrame:
    """Apply silver-layer cleansing to fact_performance."""
    df = _load_table(engine, "fact_performance")

    df["kpi_score"] = pd.to_numeric(df["kpi_score"], errors="coerce").clip(0.0, 5.0)
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce").dt.date
    df = df.dropna(subset=["performance_id", "employee_id", "review_date", "kpi_score"])

    result = validate_performance_dataframe(df)
    for err in result.errors:
        logger.error("Silver validation error: %s", err)

    logger.info("Silver cleansing: %d clean performance records", len(df))
    return df


def cleanse_teams(engine: sa.Engine) -> pd.DataFrame:
    """Apply silver-layer cleansing to dim_team."""
    df = _load_table(engine, "dim_team")

    df["annual_budget"] = pd.to_numeric(df["annual_budget"], errors="coerce")
    df = df.dropna(subset=["team_id", "team_name", "annual_budget"])
    df = df[df["annual_budget"] >= 0]

    result = validate_team_dataframe(df)
    for err in result.errors:
        logger.error("Silver validation error: %s", err)

    logger.info("Silver cleansing: %d clean team records", len(df))
    return df


def run_silver_pipeline(engine: sa.Engine) -> dict[str, int]:
    """Run full silver cleansing pass. Returns record counts."""
    employees = cleanse_employees(engine)
    performance = cleanse_performance(engine)
    teams = cleanse_teams(engine)
    return {
        "employees": len(employees),
        "performance": len(performance),
        "teams": len(teams),
    }


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    engine = get_engine()
    counts = run_silver_pipeline(engine)
    print("Silver layer complete:", counts)
