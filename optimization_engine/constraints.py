"""Constraint configuration and validation for the ILP workforce optimization model."""

from dataclasses import dataclass, field


@dataclass
class ConstraintConfig:
    """Settings that control which constraints are active in the ILP solve.

    Defaults enforce the most common operational requirements.
    Relax individual flags when the solver reports infeasibility to diagnose root causes.
    """

    require_leadership_per_team: bool = True
    """At least one employee at lead/director/exec level must be retained per team."""

    require_critical_skills: bool = True
    """At least one holder of each critical skill must be retained in the organization."""

    min_team_size: int = 0
    """Minimum employees retained per team (0 = no minimum)."""

    succession_depth: int = 0
    """
    If > 0, each critical-skill role requires this many retained holders as backup.
    E.g., succession_depth=1 means at least 2 holders total (primary + 1 backup).
    Disabled by default because it can quickly make problems infeasible.
    """

    time_limit_seconds: int = 30
    """CBC solver wall-clock time limit. Increase for large (>2 000 employee) problems."""

    solver_msg: bool = False
    """Pipe CBC solver stdout to Python logger when True (useful for debugging)."""


# Leadership seniority levels that satisfy the leadership constraint
LEADERSHIP_LEVELS: frozenset[str] = frozenset({"lead", "director", "exec"})


def validate_config(config: ConstraintConfig) -> list[str]:
    """Return a list of configuration warnings (empty = config is clean)."""
    warnings: list[str] = []
    if config.min_team_size < 0:
        warnings.append("min_team_size must be >= 0; treating as 0.")
    if config.succession_depth < 0:
        warnings.append("succession_depth must be >= 0; treating as 0.")
    if config.time_limit_seconds < 1:
        warnings.append("time_limit_seconds < 1 will immediately time out the solver.")
    return warnings
