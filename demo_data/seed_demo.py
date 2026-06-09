"""CLI tool to seed the demo database.

Usage:
    python demo_data/seed_demo.py --scenario all --size medium
    python demo_data/seed_demo.py --scenario A --size small
    python demo_data/seed_demo.py --scenario B --size large
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_pipeline.bronze_ingest import get_engine
from demo_data.generator import DemoGenerator, GeneratedOrg
from demo_data.scenarios import ALL_SCENARIOS, ALL_SIZES

load_dotenv()
logger = logging.getLogger(__name__)


def _upsert_dataframe(
    df: pd.DataFrame,
    table: str,
    engine: sa.Engine,
    chunksize: int = 500,
) -> None:
    """Write DataFrame to table, ignoring conflicts on primary key."""
    if df.empty:
        return
    with engine.begin() as conn:
        df.to_sql(table, conn, if_exists="append", index=False,
                  method="multi", chunksize=chunksize)


def _drop_internal_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Remove generator-internal columns not present in schema."""
    internal = [c for c in df.columns if c.startswith("_")]
    return df.drop(columns=internal, errors="ignore")


def seed_organization(org: GeneratedOrg, engine: sa.Engine) -> None:
    """Insert a generated org into PostgreSQL."""
    t0 = time.time()
    logger.info(
        "Seeding org '%s' [scenario=%s, size=%s] …",
        org.org_name, org.scenario_id, org.org_size,
    )

    # dim_team
    _upsert_dataframe(org.teams, "dim_team", engine)
    logger.info("  ↳ teams: %d rows", len(org.teams))

    # dim_employee (drop internal marker columns)
    emp_clean = _drop_internal_cols(org.employees)
    _upsert_dataframe(emp_clean, "dim_employee", engine)
    logger.info("  ↳ employees: %d rows", len(emp_clean))

    # Update team manager_id now that employees exist
    with engine.begin() as conn:
        for _, team in org.teams.iterrows():
            if team["manager_id"]:
                conn.execute(
                    sa.text(
                        "UPDATE dim_team SET manager_id = :mgr WHERE team_id = :tid"
                    ),
                    {"mgr": team["manager_id"], "tid": team["team_id"]},
                )

    # skills (global — use INSERT … ON CONFLICT DO NOTHING to avoid duplicates)
    with engine.begin() as conn:
        for _, skill in org.skills.iterrows():
            conn.execute(
                sa.text(
                    "INSERT INTO skills (skill_id, skill_name, category, is_critical, market_scarcity) "
                    "VALUES (:sid, :name, :cat, :crit, :scar) "
                    "ON CONFLICT (skill_name) DO NOTHING"
                ),
                {
                    "sid": skill["skill_id"],
                    "name": skill["skill_name"],
                    "cat": skill["category"],
                    "crit": bool(skill["is_critical"]),
                    "scar": float(skill["market_scarcity"]),
                },
            )
    logger.info("  ↳ skills: %d rows (upserted)", len(org.skills))

    # employee_skills — look up actual skill_ids from DB (canonical)
    with engine.connect() as conn:
        db_skills = pd.read_sql("SELECT skill_id, skill_name FROM skills", conn)
    name_to_id = dict(zip(db_skills["skill_name"], db_skills["skill_id"], strict=False))

    # Remap skill_ids in employee_skills to canonical DB values
    skill_id_map = dict(zip(org.skills["skill_id"], org.skills["skill_name"], strict=False))
    emp_skills = org.employee_skills.copy()
    emp_skills["skill_id"] = emp_skills["skill_id"].map(
        lambda sid: name_to_id.get(skill_id_map.get(sid, ""), sid)
    )
    _upsert_dataframe(emp_skills, "employee_skills", engine)
    logger.info("  ↳ employee_skills: %d rows", len(emp_skills))

    # fact_performance
    _upsert_dataframe(org.performance, "fact_performance", engine)
    logger.info("  ↳ performance: %d rows", len(org.performance))

    # fact_collaboration
    _upsert_dataframe(org.collaboration, "fact_collaboration", engine)
    logger.info("  ↳ collaboration: %d edges", len(org.collaboration))

    # fact_budget
    _upsert_dataframe(org.budget, "fact_budget", engine)
    logger.info("  ↳ budget: %d rows", len(org.budget))

    # demo_organizations metadata
    meta = pd.DataFrame([{
        "org_id": org.org_id,
        "scenario_id": org.scenario_id,
        "org_size": org.org_size,
        "org_name": org.org_name,
        "industry": org.industry,
        "description": org.description,
        "total_employees": len(org.employees),
        "annual_budget": float(org.budget["budgeted_amount"].sum()) / 12 * 4
        if not org.budget.empty else 0.0,
    }])
    _upsert_dataframe(meta, "demo_organizations", engine)

    elapsed = time.time() - t0
    logger.info("  ✓ Done in %.1fs", elapsed)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="EIBO Demo Database Seeder")
    parser.add_argument(
        "--scenario",
        choices=[*ALL_SCENARIOS, "all"],
        default="all",
        help="Scenario to seed (A, B, C, or all)",
    )
    parser.add_argument(
        "--size",
        choices=[*ALL_SIZES, "all"],
        default="medium",
        help="Organization size to seed (small, medium, large, or all)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated data without writing to DB",
    )
    args = parser.parse_args()

    scenarios = ALL_SCENARIOS if args.scenario == "all" else [args.scenario.upper()]
    sizes = ALL_SIZES if args.size == "all" else [args.size.lower()]

    engine = get_engine() if not args.validate else None

    total = 0
    for scenario_id in scenarios:
        for size in sizes:
            gen = DemoGenerator(scenario_id, size)
            org = gen.generate()

            if args.validate:
                logger.info(
                    "VALIDATE OK: scenario=%s size=%s employees=%d",
                    scenario_id, size, len(org.employees),
                )
            else:
                seed_organization(org, engine)  # type: ignore[arg-type]
            total += 1

    logger.info("Seeding complete. %d organization(s) processed.", total)


if __name__ == "__main__":
    main()
