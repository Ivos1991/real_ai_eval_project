"""Typed models for lease-expiration extraction evaluation."""

from pydantic import BaseModel, ConfigDict, Field


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    severity: str
    document_text: str
    expected_value: str | None
    expected_citation_text: str | None
    expected_behavior: str
    notes: str


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str]
    reasoning: str


class RuleMetricResult(BaseModel):
    name: str
    passed: bool
    score: float
    reason: str
    critical: bool = True


class JudgeResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    reason: str
    groundedness: float = Field(ge=0.0, le=1.0)
    reasoning_quality: float = Field(ge=0.0, le=1.0)
    ambiguity_handling: float = Field(ge=0.0, le=1.0)
    hallucination_risk: float = Field(ge=0.0, le=1.0)


class CaseEvaluationResult(BaseModel):
    case_id: str
    title: str
    severity: str
    extraction: ExtractionResult
    rule_metrics: list[RuleMetricResult]
    judge: JudgeResult
    total_score: float
    passed: bool
    failed_critical_metrics: list[str]
