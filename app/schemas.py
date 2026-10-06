from datetime import datetime

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    expected_frequency_minutes: int = Field(gt=0)
    freshness_tolerance: float = Field(default=1.5, gt=0)
    quality_rules: list[str] = Field(default_factory=list)


class SourceRead(SourceCreate):
    id: int

    model_config = {"from_attributes": True}


class SourceSummary(SourceRead):
    freshness: str
    quality: str


class RuleResultInput(BaseModel):
    rule_name: str
    passed: bool
    message: str | None = None


class CheckCreate(BaseModel):
    checked_at: datetime
    status: str = Field(pattern="^(PASSING|FAILING)$")
    rule_results: list[RuleResultInput] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class CheckRead(CheckCreate):
    id: int
    rule_results: list[RuleResultInput] = []

    model_config = {"from_attributes": True}


class StatusRead(BaseModel):
    source_id: int
    freshness: str
    quality: str
    latest_check: CheckRead | None
    history: list[CheckRead]
