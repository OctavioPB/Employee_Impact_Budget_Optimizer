"""Bronze layer: raw data ingestion from CSV/Excel files into PostgreSQL."""

import argparse
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv

from data_pipeline.validators import validate_csv_columns

load_dotenv()
logger = logging.getLogger(__name__)

_EMPLOYEE_CSV_REQUIRED = {
    "full_name", "role_title", "department", "annual_salary", "hire_date",
}
_TEAM_CSV_REQUIRED = {
    "team_name", "department", "annual_budget",
}


def get_engine() -> sa.Engine:
    """Build SQLAlchemy engine from environment variables."""
    user = os.getenv("POSTGRES_USER", "eibo_user")
    password = os.getenv("POSTGRES_PASSWORD", "eibo_local_dev")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "eibo_db")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return sa.create_engine(url, pool_pre_ping=True)


def _read_file(path: Path) -> pd.DataFrame:
    """Read CSV or Excel file into a DataFrame."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _add_uuid_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Add a UUID column if it doesn't exist."""
    if col not in df.columns:
        df = df.copy()
        df[col] = [str(uuid.uuid4()) for _ in range(len(df))]
    return df


def ingest_employees(path: Path, engine: sa.Engine) -> int:
    """
    Ingest employee CSV/Excel into bronze (dim_employee table).

    Returns number of rows inserted.
    """
    df = _read_file(path)
    result = validate_csv_columns(df, _EMPLOYEE_CSV_REQUIRED, str(path))
    if not result.is_valid:
        for err in result.errors:
            logger.error(err)
        raise ValueError(f"Employee file validation failed: {result.errors}")
    for warning in result.warnings:
        logger.warning(warning)

    df = _add_uuid_column(df, "employee_id")
    if "annual_benefits" not in df.columns:
        df["annual_benefits"] = df["annual_salary"] * 0.30
    if "seniority_level" not in df.columns:
        df["seniority_level"] = "mid"
    if "team_id" not in df.columns:
        df["team_id"] = None
    if "manager_id" not in df.columns:
        df["manager_id"] = None
    if "is_active" not in df.columns:
        df["is_active"] = True

    df["hire_date"] = pd.to_datetime(df["hire_date"]).dt.date
    df["annual_salary"] = pd.to_numeric(df["annual_salary"])
    df["annual_benefits"] = pd.to_numeric(df["annual_benefits"])

    with engine.begin() as conn:
        df.to_sql("dim_employee", conn, if_exists="append", index=False,
                  method="multi", chunksize=500)

    logger.info("Ingested %d employee records from %s", len(df), path)
    return len(df)


def ingest_teams(path: Path, engine: sa.Engine) -> int:
    """Ingest team CSV/Excel into bronze (dim_team table)."""
    df = _read_file(path)
    result = validate_csv_columns(df, _TEAM_CSV_REQUIRED, str(path))
    if not result.is_valid:
        for err in result.errors:
            logger.error(err)
        raise ValueError(f"Team file validation failed: {result.errors}")

    df = _add_uuid_column(df, "team_id")
    df["annual_budget"] = pd.to_numeric(df["annual_budget"])

    with engine.begin() as conn:
        df.to_sql("dim_team", conn, if_exists="append", index=False,
                  method="multi", chunksize=500)

    logger.info("Ingested %d team records from %s", len(df), path)
    return len(df)


def ingest_performance(path: Path, engine: sa.Engine) -> int:
    """Ingest performance CSV/Excel into fact_performance table."""
    df = _read_file(path)
    required = {"employee_id", "review_date", "review_period", "kpi_score"}
    result = validate_csv_columns(df, required, str(path))
    if not result.is_valid:
        raise ValueError(f"Performance file validation failed: {result.errors}")

    df = _add_uuid_column(df, "performance_id")
    df["review_date"] = pd.to_datetime(df["review_date"]).dt.date
    df["kpi_score"] = pd.to_numeric(df["kpi_score"])

    with engine.begin() as conn:
        df.to_sql("fact_performance", conn, if_exists="append", index=False,
                  method="multi", chunksize=500)

    logger.info("Ingested %d performance records from %s", len(df), path)
    return len(df)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="EIBO Bronze layer ingestion")
    parser.add_argument("--employees", type=Path, help="Employee CSV/Excel file")
    parser.add_argument("--teams", type=Path, help="Team CSV/Excel file")
    parser.add_argument("--performance", type=Path, help="Performance CSV/Excel file")
    args = parser.parse_args()

    engine = get_engine()
    if args.employees:
        ingest_employees(args.employees, engine)
    if args.teams:
        ingest_teams(args.teams, engine)
    if args.performance:
        ingest_performance(args.performance, engine)


if __name__ == "__main__":
    main()
