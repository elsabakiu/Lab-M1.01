from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Priority = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]


class Insight(BaseModel):
    title: str = Field(min_length=5)
    finding: str = Field(min_length=10)
    evidence: str = Field(min_length=10)
    likely_cause: str = Field(min_length=10)
    recommended_action: str = Field(min_length=10)
    priority: Priority
    confidence: Confidence
    affected_metric: str = Field(min_length=3)
