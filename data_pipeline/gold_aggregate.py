"""Gold layer: DuckDB aggregations for dashboard consumption."""

import logging
import os
from pathlib import Path

import duckdb
import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv

from data_pipeline.bronze_ingest import get_engine

load_dotenv()
logger = logging.getLogger(__name__)

_DUCKDB_PATH = os.getenv("DUCKDB_PATH", "./data/eibo_analytics.db")


def get_duckdb_conn() -> duckdb.DuckDBPyConnection:
    Path(_DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(_DUCKDB_PATH)


def _fetch(engine: sa.Engine, query: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def build_team_spend_summary(engine: sa.Engine, duck: duckdb.DuckDBPyConnection) -> None:
    """Total spend per team: actual vs budget with variance."""
    employees = _fetch(engine, """
        SELECT e.team_id, t.team_name, t.department,
               t.annual_budget,
               SUM(e.annual_salary + e.annual_benefits) AS actual_spend,
               COUNT(e.employee_id) AS headcount
        FROM dim_employee e
        JOIN dim_team t ON e.team_id = t.team_id
        WHERE e.is_active = TRUE
        GROUP BY e.team_id, t.team_name, t.department, t.annual_budget
    """)
    if employees.empty:
        logger.warning("No data for team_spend_summary")
        return
    employees["budget_variance_pct"] = (
        (employees["actual_spend"] - employees["annual_budget"])
        / employees["annual_budget"].replace(0, float("nan"))
        * 100
    ).round(2)

    duck.execute("CREATE OR REPLACE TABLE gold_team_spend AS SELECT * FROM employees")
    logger.info("Built gold_team_spend: %d teams", len(employees))


def build_performance_trends(engine: sa.Engine, duck: duckdb.DuckDBPyConnection) -> None:
    """Quarterly KPI averages by department."""
    perf = _fetch(engine, """
        SELECT e.department, p.review_period,
               AVG(p.kpi_score) AS avg_kpi,
               STDDEV(p.kpi_score) AS std_kpi,
               COUNT(*) AS n_reviews
        FROM fact_performance p
        JOIN dim_employee e ON p.employee_id = e.employee_id
        GROUP BY e.department, p.review_period
        ORDER BY e.department, p.review_period
    """)
    if perf.empty:
        logger.warning("No data for performance_trends")
        return
    duck.execute("CREATE OR REPLACE TABLE gold_performance_trends AS SELECT * FROM perf")
    logger.info("Built gold_performance_trends: %d rows", len(perf))


def build_impact_inputs(engine: sa.Engine, duck: duckdb.DuckDBPyConnection) -> None:
    """Pre-aggregated table of features needed for Impact Score computation."""
    data = _fetch(engine, """
        SELECT
            e.employee_id, e.full_name, e.role_title, e.seniority_level,
            e.department, e.team_id, e.manager_id,
            e.annual_salary, e.annual_benefits,
            e.hire_date,
            EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.hire_date)) AS tenure_years,
            AVG(p.kpi_score) AS avg_kpi,
            COALESCE(
                REGR_SLOPE(p.kpi_score, EXTRACT(EPOCH FROM p.review_date::TIMESTAMP)),
                0
            ) AS kpi_trend
        FROM dim_employee e
        LEFT JOIN fact_performance p ON e.employee_id = p.employee_id
        WHERE e.is_active = TRUE
        GROUP BY
            e.employee_id, e.full_name, e.role_title, e.seniority_level,
            e.department, e.team_id, e.manager_id,
            e.annual_salary, e.annual_benefits, e.hire_date
    """)
    if data.empty:
        logger.warning("No data for impact_inputs")
        return
    duck.execute("CREATE OR REPLACE TABLE gold_impact_inputs AS SELECT * FROM data")
    logger.info("Built gold_impact_inputs: %d employees", len(data))


def build_headcount_by_seniority(engine: sa.Engine, duck: duckdb.DuckDBPyConnection) -> None:
    """Headcount and salary distribution by department × seniority."""
    data = _fetch(engine, """
        SELECT department, seniority_level,
               COUNT(*) AS headcount,
               AVG(annual_salary) AS avg_salary,
               MIN(annual_salary) AS min_salary,
               MAX(annual_salary) AS max_salary,
               SUM(annual_salary + annual_benefits) AS total_cost
        FROM dim_employee
        WHERE is_active = TRUE
        GROUP BY department, seniority_level
    """)
    if data.empty:
        return
    duck.execute(
        "CREATE OR REPLACE TABLE gold_headcount_seniority AS SELECT * FROM data"
    )
    logger.info("Built gold_headcount_seniority: %d rows", len(data))


def run_gold_pipeline(engine: sa.Engine) -> dict[str, str]:
    """Run full gold aggregation pass."""
    duck = get_duckdb_conn()
    results: dict[str, str] = {}
    for fn in [
        build_team_spend_summary,
        build_performance_trends,
        build_impact_inputs,
        build_headcount_by_seniority,
    ]:
        try:
            fn(engine, duck)
            results[fn.__name__] = "ok"
        except Exception as exc:
            logger.error("Gold aggregation failed for %s: %s", fn.__name__, exc)
            results[fn.__name__] = f"error: {exc}"
    duck.close()
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    pg = get_engine()
    status = run_gold_pipeline(pg)
    print("Gold layer complete:", status)
