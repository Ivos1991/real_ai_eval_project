"""Focused tests for telemetry attachments in eval reports."""

from contextlib import nullcontext
from pathlib import Path
from typing import Literal, cast

import pytest

from config.settings import ApiSettings, EvalSettings, ReportingSettings, Settings, TracingSettings
from eval_harness.mock_sut import MockLeaseExpirationExtractor
from eval_harness.models import CaseEvaluationResult, EvalCase, ExtractionResult, JudgeResult, RuleMetricResult
from eval_harness.runner import LeaseExpirationEvalRunner


def _settings(evidence_mode: str) -> Settings:
    return Settings(
        eval=EvalSettings(
            cases_path=Path("cases/lease_expiration_cases.json"),
            total_score_threshold=0.8,
            citation_similarity_threshold=80.0,
            deterministic_score_weight=0.7,
            judge_score_weight=0.3,
        ),
        reporting=ReportingSettings(report_dir=Path("reports/test-telemetry")),
        tracing=TracingSettings(
            service_name="real-ai-eval-harness",
            console_exporter_enabled=False,
            evidence_mode=cast(Literal["always", "failure_only", "off"], evidence_mode),
        ),
        api=ApiSettings(
            extraction_endpoint="http://localhost:8080/extract",
            request_timeout_seconds=10.0,
        ),
    )


def _case_result(passed: bool) -> CaseEvaluationResult:
    extraction = ExtractionResult(
        value="2028-12-31",
        confidence=0.95,
        citations=["Lease Expiration Date"],
        reasoning="ok",
    )
    rule_metric = RuleMetricResult(
        name="schema_validity",
        display_name="Schema validity",
        passed=True,
        score=1.0,
        reason="ok",
    )
    judge = JudgeResult(
        score=1.0,
        passed=True,
        reason="ok",
        groundedness=1.0,
        reasoning_quality=1.0,
        ambiguity_handling=1.0,
        hallucination_risk=0.0,
    )
    return CaseEvaluationResult(
        case_id="case-1",
        title="Case 1",
        severity="normal",
        extraction=extraction,
        rule_metrics=[rule_metric],
        judge=judge,
        total_score=0.95,
        duration_ms=12.345,
        passed=passed,
        failed_critical_metrics=[] if passed else ["schema_validity"],
    )


def _case() -> EvalCase:
    return EvalCase(
        id="case-1",
        title="Case 1",
        severity="normal",
        document_text="Lease Expiration Date is December 31, 2028.",
        expected_value="2028-12-31",
        expected_citation_text="Lease Expiration Date",
        expected_outcome_label="an extracted expiration date",
        expected_outcome_slug="extracted_expiration_date",
        expected_behavior="Extract the lease expiration date.",
        notes="Test case.",
    )


@pytest.mark.unit
def test_attach_trace_evidence_adds_telemetry_attachment_for_always_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings("always")
    runner = LeaseExpirationEvalRunner(MockLeaseExpirationExtractor(), settings)

    attachments: list[tuple[str, dict]] = []
    monkeypatch.setattr("eval_harness.runner.allure.step", lambda _title: nullcontext())
    monkeypatch.setattr(
        "eval_harness.runner.attach_json",
        lambda name, payload: attachments.append((name, payload)),
    )
    monkeypatch.setattr(
        "eval_harness.runner.get_trace_spans",
        lambda trace_id: [{"trace_id": trace_id, "name": "span"}],
    )

    runner.attach_trace_evidence(
        case=_case(),
        result=_case_result(passed=True),
        trace_id="trace-123",
    )

    assert [name for name, _payload in attachments] == ["telemetry"]
    assert attachments[0][1]["trace_id"] == "trace-123"
    assert attachments[0][1]["spans"] == [{"trace_id": "trace-123", "name": "span"}]


@pytest.mark.unit
def test_attach_trace_evidence_adds_telemetry_attachment_for_failure_only_mode_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings("failure_only")
    runner = LeaseExpirationEvalRunner(MockLeaseExpirationExtractor(), settings)

    attachments: list[str] = []
    monkeypatch.setattr("eval_harness.runner.allure.step", lambda _title: nullcontext())
    monkeypatch.setattr(
        "eval_harness.runner.attach_json",
        lambda name, _payload: attachments.append(name),
    )
    monkeypatch.setattr("eval_harness.runner.get_trace_spans", lambda _trace_id: [])

    runner.attach_trace_evidence(
        case=_case(),
        result=_case_result(passed=False),
        trace_id="trace-123",
    )

    assert attachments == ["telemetry"]


@pytest.mark.unit
def test_attach_trace_evidence_skips_telemetry_for_failure_only_mode_on_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings("failure_only")
    runner = LeaseExpirationEvalRunner(MockLeaseExpirationExtractor(), settings)

    attachments: list[str] = []
    monkeypatch.setattr("eval_harness.runner.allure.step", lambda _title: nullcontext())
    monkeypatch.setattr(
        "eval_harness.runner.attach_json",
        lambda name, _payload: attachments.append(name),
    )
    monkeypatch.setattr("eval_harness.runner.get_trace_spans", lambda _trace_id: [])

    runner.attach_trace_evidence(
        case=_case(),
        result=_case_result(passed=True),
        trace_id="trace-123",
    )

    assert attachments == []
