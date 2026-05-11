"""Synthetic demo data generator for EIBO.

Generates realistic organizational data for three scenarios × three org sizes.
All randomness is seeded for reproducibility.
"""

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker


def _seeded_uuid(rng: np.random.Generator) -> str:
    """Generate a UUID that is deterministic given the numpy RNG state."""
    hi = int(rng.integers(0, 2**62, dtype=np.int64))
    lo = int(rng.integers(0, 2**62, dtype=np.int64))
    int_val = (hi << 66) ^ (lo << 4) ^ int(rng.integers(0, 16, dtype=np.int64))
    return str(uuid.UUID(int=int_val & ((1 << 128) - 1)))

from demo_data.scenarios import (
    ScenarioConfig,
    SKILL_TAXONOMY,
    get_base_budget,
    get_headcount,
    load_scenario,
)

logger = logging.getLogger(__name__)

_SEED = 42
fake = Faker("en_US")
Faker.seed(_SEED)

# ---------------------------------------------------------------------------
# Role taxonomy: seniority → salary (mean, std, USD annual)
# ---------------------------------------------------------------------------
_ROLE_SALARY: dict[str, dict[str, tuple[float, float]]] = {
    "Engineering": {
        "junior":   (75_000,  8_000),
        "mid":      (115_000, 12_000),
        "senior":   (155_000, 18_000),
        "lead":     (185_000, 20_000),
        "director": (230_000, 25_000),
        "exec":     (320_000, 40_000),
    },
    "Product": {
        "junior":   (70_000,  7_000),
        "mid":      (105_000, 10_000),
        "senior":   (140_000, 15_000),
        "lead":     (170_000, 18_000),
        "director": (210_000, 22_000),
        "exec":     (290_000, 35_000),
    },
    "Sales": {
        "junior":   (55_000, 10_000),
        "mid":      (80_000, 15_000),
        "senior":   (115_000, 20_000),
        "lead":     (140_000, 22_000),
        "director": (175_000, 25_000),
        "exec":     (250_000, 35_000),
    },
    "default": {
        "junior":   (58_000,  7_000),
        "mid":      (85_000, 10_000),
        "senior":   (115_000, 13_000),
        "lead":     (140_000, 16_000),
        "director": (175_000, 20_000),
        "exec":     (240_000, 30_000),
    },
}

_SENIORITY_DISTRIBUTION = [
    ("junior",  0.20),
    ("mid",     0.35),
    ("senior",  0.28),
    ("lead",    0.10),
    ("director",0.05),
    ("exec",    0.02),
]

_ROLE_BY_DEPT_SENIORITY: dict[str, dict[str, str]] = {
    "Engineering": {
        "junior": "Junior Software Engineer",
        "mid": "Software Engineer",
        "senior": "Senior Software Engineer",
        "lead": "Engineering Manager",
        "director": "Director of Engineering",
        "exec": "VP of Engineering",
    },
    "Product": {
        "junior": "Associate Product Manager",
        "mid": "Product Manager",
        "senior": "Senior Product Manager",
        "lead": "Group Product Manager",
        "director": "Director of Product",
        "exec": "VP of Product",
    },
    "Sales": {
        "junior": "Sales Development Representative",
        "mid": "Account Executive",
        "senior": "Senior Account Executive",
        "lead": "Sales Manager",
        "director": "Director of Sales",
        "exec": "VP of Sales",
    },
    "Marketing": {
        "junior": "Marketing Coordinator",
        "mid": "Marketing Manager",
        "senior": "Senior Marketing Manager",
        "lead": "Marketing Director",
        "director": "Director of Marketing",
        "exec": "VP of Marketing",
    },
    "Operations": {
        "junior": "Operations Coordinator",
        "mid": "Operations Analyst",
        "senior": "Senior Operations Manager",
        "lead": "Operations Manager",
        "director": "Director of Operations",
        "exec": "VP of Operations",
    },
    "Finance": {
        "junior": "Financial Analyst",
        "mid": "Senior Financial Analyst",
        "senior": "Finance Manager",
        "lead": "Senior Finance Manager",
        "director": "Director of Finance",
        "exec": "CFO",
    },
    "Risk & Compliance": {
        "junior": "Compliance Analyst",
        "mid": "Risk Analyst",
        "senior": "Senior Risk Manager",
        "lead": "Risk Manager",
        "director": "Director of Risk",
        "exec": "Chief Risk Officer",
    },
    "Clinical": {
        "junior": "Clinical Coordinator",
        "mid": "Clinical Analyst",
        "senior": "Senior Clinical Specialist",
        "lead": "Clinical Manager",
        "director": "Director of Clinical Operations",
        "exec": "Chief Medical Officer",
    },
    "Technology": {
        "junior": "Junior Developer",
        "mid": "Software Developer",
        "senior": "Senior Developer",
        "lead": "Tech Lead",
        "director": "Director of Technology",
        "exec": "CTO",
    },
    "HR & People": {
        "junior": "HR Coordinator",
        "mid": "HR Business Partner",
        "senior": "Senior HR Business Partner",
        "lead": "HR Manager",
        "director": "Director of People",
        "exec": "Chief People Officer",
    },
}

_DEPT_SKILLS: dict[str, list[str]] = {
    "Engineering":     ["Python", "Java", "Go", "TypeScript", "React", "Kubernetes",
                        "Terraform", "AWS", "PostgreSQL", "Apache Kafka", "Machine Learning",
                        "DevOps", "Security Engineering"],
    "Product":         ["Strategic Planning", "Data Analysis", "Communication",
                        "Problem Solving", "People Management"],
    "Sales":           ["Communication", "Strategic Planning", "Data Analysis",
                        "Budget Management", "Problem Solving"],
    "Marketing":       ["Communication", "Data Analysis", "Problem Solving"],
    "Operations":      ["Strategic Planning", "Budget Management", "Data Analysis",
                        "People Management", "Problem Solving"],
    "Finance":         ["Budget Management", "Data Analysis", "Problem Solving",
                        "Strategic Planning"],
    "Risk & Compliance":["RegTech", "HIPAA Compliance", "Strategic Planning",
                         "Data Analysis", "Problem Solving"],
    "Technology":      ["COBOL", "Java", "Python", "AWS", "PostgreSQL", "Data Analysis"],
    "Clinical":        ["HIPAA Compliance", "HL7/FHIR", "Data Analysis",
                        "Strategic Planning", "Communication"],
    "HR & People":     ["People Management", "Communication", "Budget Management",
                        "Strategic Planning", "Data Analysis"],
}


@dataclass
class GeneratedOrg:
    org_id: str
    scenario_id: str
    org_size: str
    org_name: str
    industry: str
    description: str
    teams: pd.DataFrame
    employees: pd.DataFrame
    performance: pd.DataFrame
    skills: pd.DataFrame
    employee_skills: pd.DataFrame
    collaboration: pd.DataFrame
    budget: pd.DataFrame


class DemoGenerator:
    """Generates a complete synthetic organization for a given scenario × size."""

    def __init__(self, scenario_id: str, org_size: str, seed: int = _SEED) -> None:
        self.scenario = load_scenario(scenario_id)
        self.org_size = org_size.lower()
        self.target_headcount = get_headcount(self.org_size)
        self.base_budget = get_base_budget(self.org_size)
        self.rng = np.random.default_rng(seed)
        random.seed(seed)
        Faker.seed(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> GeneratedOrg:
        org_id = _seeded_uuid(self.rng)
        org_name = self._org_name()
        logger.info(
            "Generating org '%s' | scenario=%s | size=%s | headcount=%d",
            org_name, self.scenario.id, self.org_size, self.target_headcount,
        )

        teams_df = self._generate_teams(org_id)
        employees_df = self._generate_employees(teams_df, org_id)
        performance_df = self._generate_performance(employees_df)
        skills_df = self._generate_skills()
        emp_skills_df = self._assign_skills(employees_df, skills_df)
        collab_df = self._generate_collaboration(employees_df)
        budget_df = self._generate_budget(teams_df)

        return GeneratedOrg(
            org_id=org_id,
            scenario_id=self.scenario.id,
            org_size=self.org_size,
            org_name=org_name,
            industry=self.scenario.industry,
            description=self.scenario.description,
            teams=teams_df,
            employees=employees_df,
            performance=performance_df,
            skills=skills_df,
            employee_skills=emp_skills_df,
            collaboration=collab_df,
            budget=budget_df,
        )

    # ------------------------------------------------------------------
    # Internal generators
    # ------------------------------------------------------------------

    def _org_name(self) -> str:
        adjectives = ["Apex", "Vertex", "Meridian", "Nexus", "Crest",
                      "Summit", "Pinnacle", "Harbor", "Zenith", "Atlas"]
        nouns = ["Systems", "Solutions", "Technologies", "Ventures",
                 "Partners", "Group", "Dynamics", "Analytics", "Labs"]
        return f"{self.rng.choice(adjectives)} {self.rng.choice(nouns)}"

    def _generate_teams(self, org_id: str) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        budget_variance = self.scenario.total_budget_variance

        for dept_cfg in self.scenario.departments:
            dept = dept_cfg["name"]
            dept_headcount = max(
                1, round(self.target_headcount * dept_cfg["headcount_pct"])
            )
            n_teams = max(1, dept_headcount // 10)

            dept_budget = (
                self.base_budget
                * dept_cfg["headcount_pct"]
                * dept_cfg["budget_multiplier"]
            )
            per_team_budget = dept_budget / n_teams

            for i in range(n_teams):
                team_id = _seeded_uuid(self.rng)
                team_num = "" if n_teams == 1 else f" {i + 1}"
                rows.append({
                    "team_id": team_id,
                    "team_name": f"{dept} Team{team_num}",
                    "department": dept,
                    "cost_center": f"CC-{dept[:3].upper()}-{i + 1:02d}",
                    "parent_team_id": None,
                    "manager_id": None,
                    "annual_budget": round(per_team_budget, 2),
                    "scenario_id": self.scenario.id,
                    "org_size": self.org_size,
                })

        return pd.DataFrame(rows)

    def _generate_employees(self, teams_df: pd.DataFrame, org_id: str) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        dept_teams: dict[str, list[str]] = {}
        for _, t in teams_df.iterrows():
            dept_teams.setdefault(t["department"], []).append(t["team_id"])

        today = date.today()
        seniority_levels = [s for s, _ in _SENIORITY_DISTRIBUTION]
        seniority_weights = np.array([w for _, w in _SENIORITY_DISTRIBUTION])
        seniority_weights = seniority_weights / seniority_weights.sum()

        nexus_fraction = self.scenario.nexus_employee_fraction

        for dept_cfg in self.scenario.departments:
            dept = dept_cfg["name"]
            dept_headcount = max(
                1, round(self.target_headcount * dept_cfg["headcount_pct"])
            )
            team_ids = dept_teams.get(dept, [])
            if not team_ids:
                continue

            for i in range(dept_headcount):
                emp_id = _seeded_uuid(self.rng)
                seniority = str(
                    self.rng.choice(seniority_levels, p=seniority_weights)
                )
                role_titles = _ROLE_BY_DEPT_SENIORITY.get(dept, _ROLE_BY_DEPT_SENIORITY["HR & People"])
                role_title = role_titles.get(seniority, "Specialist")

                salary_table = _ROLE_SALARY.get(dept, _ROLE_SALARY["default"])
                sal_mean, sal_std = salary_table[seniority]
                salary = max(30_000, round(float(self.rng.normal(sal_mean, sal_std)), -2))

                # Nexus employees: inflate salary slightly, mark for high centrality
                is_nexus = self.rng.random() < nexus_fraction

                tenure_days = int(self.rng.integers(90, 365 * 12))
                hire_date = today - timedelta(days=tenure_days)

                team_id = str(self.rng.choice(team_ids))
                rows.append({
                    "employee_id": emp_id,
                    "full_name": fake.name(),
                    "email": fake.company_email(),
                    "role_title": role_title,
                    "seniority_level": seniority,
                    "department": dept,
                    "team_id": team_id,
                    "manager_id": None,
                    "hire_date": hire_date.isoformat(),
                    "annual_salary": salary,
                    "annual_benefits": round(salary * 0.30, 2),
                    "is_active": True,
                    "location": fake.city(),
                    "scenario_id": self.scenario.id,
                    "org_size": self.org_size,
                    "_is_nexus": is_nexus,
                })

        df = pd.DataFrame(rows)
        df = self._assign_managers(df, teams_df)
        return df

    def _assign_managers(
        self, employees_df: pd.DataFrame, teams_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Set manager_id: each team's lead/director manages within-team peers."""
        df = employees_df.copy()
        senior_ranks = {"lead", "director", "exec"}

        for team_id in df["team_id"].unique():
            team_emps = df[df["team_id"] == team_id]
            seniors = team_emps[team_emps["seniority_level"].isin(senior_ranks)]
            if seniors.empty:
                manager_id = team_emps.iloc[0]["employee_id"]
            else:
                manager_id = seniors.iloc[0]["employee_id"]

            mask = (df["team_id"] == team_id) & (df["employee_id"] != manager_id)
            df.loc[mask, "manager_id"] = manager_id

        teams_df_copy = teams_df.copy()
        for _, team in teams_df.iterrows():
            team_emps = df[df["team_id"] == team["team_id"]]
            if not team_emps.empty:
                mgr = team_emps[
                    team_emps["seniority_level"].isin(senior_ranks)
                ]
                mgr_id = mgr.iloc[0]["employee_id"] if not mgr.empty else team_emps.iloc[0]["employee_id"]
                teams_df_copy.loc[teams_df_copy["team_id"] == team["team_id"], "manager_id"] = mgr_id

        return df

    def _generate_performance(self, employees_df: pd.DataFrame) -> pd.DataFrame:
        """Generate 12 quarterly performance reviews per employee over 3 years."""
        rows: list[dict[str, Any]] = []
        today = date.today()

        seniority_baseline = {
            "junior": 3.0, "mid": 3.4, "senior": 3.7,
            "lead": 3.8, "director": 3.9, "exec": 4.0,
        }

        for _, emp in employees_df.iterrows():
            base_kpi = seniority_baseline.get(emp["seniority_level"], 3.4)
            # Individual performance personality: consistent performer vs variable
            personal_std = float(self.rng.uniform(0.1, 0.5))
            trend = float(self.rng.uniform(-0.02, 0.04))  # per-quarter trend

            hire_date = date.fromisoformat(str(emp["hire_date"]))
            quarters_employed = min(12, max(1, (today - hire_date).days // 90))

            for q in range(quarters_employed):
                review_date = today - timedelta(days=q * 90)
                year = review_date.year
                quarter = (review_date.month - 1) // 3 + 1
                period = f"{year}-Q{quarter}"

                # Seasonality: Q4 slightly inflated (year-end bias)
                seasonal = 0.1 if quarter == 4 else 0.0

                kpi = base_kpi + trend * q + seasonal + float(
                    self.rng.normal(0, personal_std)
                )
                kpi = float(np.clip(kpi, 1.0, 5.0))

                rows.append({
                    "performance_id": _seeded_uuid(self.rng),
                    "employee_id": emp["employee_id"],
                    "review_date": review_date.isoformat(),
                    "review_period": period,
                    "kpi_score": round(kpi, 2),
                    "goals_met_pct": round(float(np.clip(kpi / 5.0 * 100, 20, 100)), 1),
                    "manager_rating": round(float(np.clip(kpi + self.rng.normal(0, 0.2), 1, 5)), 2),
                    "peer_rating": round(float(np.clip(kpi + self.rng.normal(0, 0.3), 1, 5)), 2),
                    "notes": None,
                })

        return pd.DataFrame(rows)

    def _generate_skills(self) -> pd.DataFrame:
        rows = []
        for skill_name, attrs in SKILL_TAXONOMY.items():
            rows.append({
                "skill_id": _seeded_uuid(self.rng),
                "skill_name": skill_name,
                "category": attrs["category"],
                "is_critical": attrs["is_critical"],
                "market_scarcity": attrs["market_scarcity"],
            })
        return pd.DataFrame(rows)

    def _assign_skills(
        self, employees_df: pd.DataFrame, skills_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Assign 2–6 skills per employee based on department affinity."""
        skill_name_to_id = dict(zip(skills_df["skill_name"], skills_df["skill_id"]))
        rows: list[dict[str, Any]] = []

        seniority_n_skills = {
            "junior": (2, 3), "mid": (3, 4), "senior": (4, 5),
            "lead": (4, 6), "director": (5, 6), "exec": (4, 6),
        }

        for _, emp in employees_df.iterrows():
            dept = emp["department"]
            dept_skills = _DEPT_SKILLS.get(dept, list(SKILL_TAXONOMY.keys())[:5])
            lo, hi = seniority_n_skills.get(emp["seniority_level"], (3, 5))
            n_skills = int(self.rng.integers(lo, hi + 1))
            n_skills = min(n_skills, len(dept_skills))

            chosen = list(self.rng.choice(dept_skills, size=n_skills, replace=False))

            # Nexus employees get at least one critical skill
            critical = [s for s in dept_skills if SKILL_TAXONOMY.get(s, {}).get("is_critical")]
            if emp.get("_is_nexus") and critical and chosen:
                critical_pick = str(self.rng.choice(critical))
                if critical_pick not in chosen:
                    chosen[0] = critical_pick

            for idx, skill_name in enumerate(chosen):
                skill_id = skill_name_to_id.get(skill_name)
                if not skill_id:
                    continue
                # Senior employees have higher proficiency
                seniority_prof = {
                    "junior": (0.3, 0.5), "mid": (0.5, 0.7), "senior": (0.65, 0.85),
                    "lead": (0.7, 0.9), "director": (0.75, 0.95), "exec": (0.7, 0.9),
                }
                lo_p, hi_p = seniority_prof.get(emp["seniority_level"], (0.5, 0.8))
                prof = round(float(self.rng.uniform(lo_p, hi_p)), 3)
                rows.append({
                    "employee_id": emp["employee_id"],
                    "skill_id": skill_id,
                    "proficiency": prof,
                    "is_primary": idx == 0,
                })

        return pd.DataFrame(rows)

    def _generate_collaboration(self, employees_df: pd.DataFrame) -> pd.DataFrame:
        """Generate collaboration edges: reports_to, collaborates_with, mentors."""
        rows: list[dict[str, Any]] = []
        emp_ids = employees_df["employee_id"].tolist()
        emp_depts = dict(zip(employees_df["employee_id"], employees_df["department"]))
        emp_managers = dict(zip(employees_df["employee_id"], employees_df["manager_id"]))
        emp_teams = dict(zip(employees_df["employee_id"], employees_df["team_id"]))
        emp_seniority = dict(zip(employees_df["employee_id"], employees_df["seniority_level"]))

        nexus_ids = set(
            employees_df[employees_df.get("_is_nexus", False) == True]["employee_id"].tolist()
            if "_is_nexus" in employees_df.columns
            else []
        )

        added: set[tuple[str, str, str]] = set()

        def add_edge(src: str, tgt: str, rel: str, weight: float) -> None:
            key = (src, tgt, rel)
            if key not in added and src != tgt:
                added.add(key)
                rows.append({
                    "source_id": src,
                    "target_id": tgt,
                    "relationship_type": rel,
                    "interaction_weight": round(weight, 3),
                    "period": "current",
                })

        for emp_id in emp_ids:
            mgr_id = emp_managers.get(emp_id)
            if mgr_id and pd.notna(mgr_id):
                add_edge(emp_id, str(mgr_id), "reports_to", 0.9)

            # Peer collaborations within team
            team_peers = [
                e for e in emp_ids
                if emp_teams.get(e) == emp_teams.get(emp_id) and e != emp_id
            ]
            n_peer_collab = min(len(team_peers), int(self.rng.integers(2, 6)))
            if team_peers:
                peers = list(
                    self.rng.choice(team_peers, size=n_peer_collab, replace=False)
                )
                for peer in peers:
                    w = float(self.rng.uniform(0.4, 0.85))
                    add_edge(emp_id, str(peer), "collaborates_with", w)

            # Cross-team collaborations (1–3 per employee, more for nexus)
            other_dept = [
                e for e in emp_ids
                if emp_depts.get(e) != emp_depts.get(emp_id)
            ]
            n_cross = int(self.rng.integers(1, 5 if emp_id in nexus_ids else 3))
            n_cross = min(n_cross, len(other_dept))
            if other_dept and n_cross > 0:
                cross = list(
                    self.rng.choice(other_dept, size=n_cross, replace=False)
                )
                for ct in cross:
                    w = float(self.rng.uniform(0.15, 0.45))
                    add_edge(emp_id, str(ct), "collaborates_with", w)

            # Mentoring relationships (senior → junior, same department)
            seniority = emp_seniority.get(emp_id, "mid")
            if seniority in {"senior", "lead", "director", "exec"}:
                juniors = [
                    e for e in emp_ids
                    if emp_depts.get(e) == emp_depts.get(emp_id)
                    and emp_seniority.get(e) in {"junior", "mid"}
                    and e != emp_id
                ]
                if juniors:
                    mentee = str(self.rng.choice(juniors))
                    add_edge(emp_id, mentee, "mentors", float(self.rng.uniform(0.5, 0.8)))

        return pd.DataFrame(rows)

    def _generate_budget(self, teams_df: pd.DataFrame) -> pd.DataFrame:
        """Generate quarterly budget actuals for the past 3 years."""
        rows: list[dict[str, Any]] = []
        today = date.today()

        for _, team in teams_df.iterrows():
            annual_budget = team["annual_budget"]
            quarterly_budget = annual_budget / 4

            dept_cfg = next(
                (d for d in self.scenario.departments if d["name"] == team["department"]),
                {"budget_multiplier": 1.0},
            )
            overrun = dept_cfg["budget_multiplier"]

            for q_offset in range(12):  # 12 quarters = 3 years
                period_end = today - timedelta(days=q_offset * 91)
                period_start = period_end - timedelta(days=90)
                year = period_start.year
                quarter = (period_start.month - 1) // 3 + 1
                period = f"{year}-Q{quarter}"

                # Actual spend: budget × overrun × seasonal noise
                seasonal = 1.1 if quarter == 4 else 1.0
                noise = float(self.rng.uniform(0.92, 1.08))
                actual = round(quarterly_budget * overrun * seasonal * noise, 2)

                rows.append({
                    "budget_id": _seeded_uuid(self.rng),
                    "team_id": team["team_id"],
                    "fiscal_period": period,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "budgeted_amount": round(quarterly_budget, 2),
                    "actual_amount": actual,
                    "headcount_plan": max(1, int(annual_budget / 120_000 / 4)),
                    "headcount_actual": max(1, int(actual / 30_000)),
                })

        return pd.DataFrame(rows)
