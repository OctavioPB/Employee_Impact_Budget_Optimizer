"""Shared request field types, so every endpoint validates scenario/size the same way."""

from typing import Annotated

from pydantic import Field

ScenarioId = Annotated[str, Field(pattern="^[ABCabc]$")]
OrgSize    = Annotated[str, Field(pattern="^(small|medium|large)$")]
