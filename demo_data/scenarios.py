"""Pre-built demo scenario definitions for EIBO."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCENARIOS_DIR = Path(__file__).parent / "organizations"

_SIZE_HEADCOUNT = {
    "small": 50,
    "medium": 500,
    "large": 5000,
}

_SIZE_BASE_BUDGET = {
    "small":  4_000_000,
    "medium": 45_000_000,
    "large":  500_000_000,
}


@dataclass(frozen=True)
class ScenarioConfig:
    id: str
    name: str
    industry: str
    description: str
    departments: list[dict[str, Any]]
    challenges: list[str]
    total_budget_variance: float
    nexus_employee_fraction: float
    critical_skill_gaps: list[str]


def load_scenario(scenario_id: str) -> ScenarioConfig:
    """Load scenario config from JSON file. scenario_id must be 'A', 'B', or 'C'."""
    id_upper = scenario_id.upper()
    mapping = {"A": "scenario_a_growing", "B": "scenario_b_restructuring", "C": "scenario_c_merger"}
    if id_upper not in mapping:
        raise ValueError(f"Unknown scenario '{scenario_id}'. Valid: A, B, C")

    path = _SCENARIOS_DIR / f"{mapping[id_upper]}.json"
    with open(path) as fh:
        data = json.load(fh)

    return ScenarioConfig(
        id=data["id"],
        name=data["name"],
        industry=data["industry"],
        description=data["description"],
        departments=data["departments"],
        challenges=data["challenges"],
        total_budget_variance=data["total_budget_variance"],
        nexus_employee_fraction=data["nexus_employee_fraction"],
        critical_skill_gaps=data["critical_skill_gaps"],
    )


def get_headcount(size: str) -> int:
    size_lower = size.lower()
    if size_lower not in _SIZE_HEADCOUNT:
        raise ValueError(f"Unknown org size '{size}'. Valid: small, medium, large")
    return _SIZE_HEADCOUNT[size_lower]


def get_base_budget(size: str) -> float:
    return _SIZE_BASE_BUDGET[size.lower()]


ALL_SCENARIOS = ["A", "B", "C"]
ALL_SIZES = ["small", "medium", "large"]


SKILL_TAXONOMY: dict[str, dict[str, Any]] = {
    # Technical — engineering
    "Python":              {"category": "technical", "is_critical": False, "market_scarcity": 0.20},
    "Java":                {"category": "technical", "is_critical": False, "market_scarcity": 0.25},
    "Go":                  {"category": "technical", "is_critical": False, "market_scarcity": 0.40},
    "Rust":                {"category": "technical", "is_critical": False, "market_scarcity": 0.65},
    "TypeScript":          {"category": "technical", "is_critical": False, "market_scarcity": 0.22},
    "React":               {"category": "technical", "is_critical": False, "market_scarcity": 0.25},
    "Kubernetes":          {"category": "technical", "is_critical": True,  "market_scarcity": 0.50},
    "Terraform":           {"category": "technical", "is_critical": True,  "market_scarcity": 0.55},
    "AWS":                 {"category": "technical", "is_critical": False, "market_scarcity": 0.30},
    "Azure":               {"category": "technical", "is_critical": False, "market_scarcity": 0.32},
    "GCP":                 {"category": "technical", "is_critical": False, "market_scarcity": 0.38},
    "PostgreSQL":          {"category": "technical", "is_critical": False, "market_scarcity": 0.20},
    "Apache Kafka":        {"category": "technical", "is_critical": True,  "market_scarcity": 0.60},
    "Spark":               {"category": "technical", "is_critical": True,  "market_scarcity": 0.55},
    "Machine Learning":    {"category": "technical", "is_critical": True,  "market_scarcity": 0.58},
    "DevOps":              {"category": "technical", "is_critical": True,  "market_scarcity": 0.55},
    "Security Engineering":{"category": "technical", "is_critical": True,  "market_scarcity": 0.72},
    "COBOL":               {"category": "technical", "is_critical": True,  "market_scarcity": 0.85},
    "HIPAA Compliance":    {"category": "domain",    "is_critical": True,  "market_scarcity": 0.75},
    "HL7/FHIR":            {"category": "domain",    "is_critical": True,  "market_scarcity": 0.78},
    "RegTech":             {"category": "domain",    "is_critical": True,  "market_scarcity": 0.70},
    # Leadership
    "Strategic Planning":  {"category": "leadership","is_critical": True,  "market_scarcity": 0.60},
    "Executive Presence":  {"category": "leadership","is_critical": False, "market_scarcity": 0.55},
    "Budget Management":   {"category": "leadership","is_critical": False, "market_scarcity": 0.40},
    "People Management":   {"category": "leadership","is_critical": False, "market_scarcity": 0.35},
    # Soft skills
    "Communication":       {"category": "soft",      "is_critical": False, "market_scarcity": 0.15},
    "Problem Solving":     {"category": "soft",      "is_critical": False, "market_scarcity": 0.15},
    "Data Analysis":       {"category": "soft",      "is_critical": False, "market_scarcity": 0.25},
}
