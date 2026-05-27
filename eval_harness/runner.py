"""Scenario runner for lease-expiration eval cases."""

import time

import allure
from assertpy import assert_that
from config.settings import Settings
from core.reporting import attach_json, attach_text
from eval_harness.evaluators.mock_llm_judge import MockLLMJudge
from eval_harness.evaluators.rule_based import RuleBasedEvaluator
from eval_harness.mock_sut import MockLeaseExpirationExtractor
from eval_harness.models import CaseEvaluationResult, EvalCase, ExtractionResult, JudgeResult, RuleMetricResult
from eval_harness.tracing import get_trace_spans, get_tracer


class LeaseExpirationEvalRunner:
    """Coordinates extraction, scoring, reporting attachments, and quality-gate assertions."""

    def __init__(self, extractor: MockLeaseExpirationExtractor, settings: Settings) -> None:
        self._extractor = extractor
        self._settings = settings
        self._rule_evaluator = RuleBasedEvaluator(settings.eval.citation_similarity_threshold)
        self._judge = MockLLMJudge()

    def run_case(self, case: EvalCase) -> CaseEvaluationResult:
        started_at = time.perf_counter()
        self._set_allure_metadata(case)
        trace_id: str

        with get_tracer().start_as_current_span("eval.case") as span:
            span.set_attribute("case.id", case.id)
            span.set_attribute("case.title", case.title)
            span.set_attribute("case.severity", case.severity)
            span.set_attribute("field.name", "lease_expiration_date")
            trace_id = f"{span.get_span_context().trace_id:032x}"

            with allure.step("Attach eval case"):
                attach_json("input_case", case.model_dump())
                attach_json(
                    "expected_output",
                    {
                        "expected_value": case.expected_value,
                        "expected_citation_text": case.expected_citation_text,
                        "expected_outcome_label": case.expected_outcome_label,
                        "expected_behavior": case.expected_behavior,
                    },
                )

            extraction = self.extract_value(case)
            rule_metrics = self.score_with_rules(case, extraction)
            judge = self.score_with_mock_judge(case, extraction)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            result = self.build_result(case, extraction, rule_metrics, judge, duration_ms)
            span.set_attribute("eval.total_score", result.total_score)
            span.set_attribute("eval.passed", result.passed)
            span.set_attribute("eval.duration_ms", result.duration_ms)

            with allure.step("Attach eval scores"):
                attach_json("scores", result.model_dump())
                attach_text("human_readable_eval_summary", self._human_readable_summary(case, result))

        self.attach_trace_evidence(case, result, trace_id)

        return result

    def extract_value(self, case: EvalCase) -> ExtractionResult:
        with allure.step("Run mock lease-expiration extractor"):
            extraction = self._extractor.extract(case.document_text)
            attach_json("actual_output", extraction.model_dump())
            return extraction

    def score_with_rules(self, case: EvalCase, extraction: ExtractionResult) -> list[RuleMetricResult]:
        with allure.step("Score deterministic metrics"):
            metrics = self._rule_evaluator.score(case, extraction)
            attach_json("rule_based_metrics", [metric.model_dump() for metric in metrics])
            return metrics

    def score_with_mock_judge(self, case: EvalCase, extraction: ExtractionResult) -> JudgeResult:
        with allure.step("Score mock LLM judge rubric"):
            judge = self._judge.score(case, extraction)
            attach_json("mock_llm_judge", judge.model_dump())
            return judge

    def build_result(
        self,
        case: EvalCase,
        extraction: ExtractionResult,
        rule_metrics: list[RuleMetricResult],
        judge: JudgeResult,
        duration_ms: float,
    ) -> CaseEvaluationResult:
        deterministic_score = sum(metric.score for metric in rule_metrics) / len(rule_metrics)
        total_score = round(
            (deterministic_score * self._settings.eval.deterministic_score_weight)
            + (judge.score * self._settings.eval.judge_score_weight),
            3,
        )
        failed_critical_metrics = [metric.name for metric in rule_metrics if metric.critical and not metric.passed]
        passed = (
            not failed_critical_metrics
            and judge.passed
            and total_score >= self._settings.eval.total_score_threshold
        )

        return CaseEvaluationResult(
            case_id=case.id,
            title=case.title,
            severity=case.severity,
            extraction=extraction,
            rule_metrics=rule_metrics,
            judge=judge,
            total_score=total_score,
            duration_ms=duration_ms,
            passed=passed,
            failed_critical_metrics=failed_critical_metrics,
        )

    def assert_quality_gate_passed(self, result: CaseEvaluationResult) -> None:
        with allure.step("Assert eval quality gate"):
            assert_that(result.failed_critical_metrics).described_as(
                "critical deterministic metric failures"
            ).is_empty()
            assert_that(result.judge.passed).described_as("mock LLM judge pass status").is_true()
            assert_that(result.total_score).described_as("total eval score").is_greater_than_or_equal_to(
                self._settings.eval.total_score_threshold
            )

    def attach_trace_evidence(self, case: EvalCase, result: CaseEvaluationResult, trace_id: str) -> None:
        mode = self._settings.tracing.evidence_mode
        should_attach = mode == "always" or (mode == "failure_only" and not result.passed)
        if not should_attach:
            return

        with allure.step("Attach OpenTelemetry trace evidence"):
            attach_json(
                f"trace_spans_{case.id}",
                {
                    "case_id": case.id,
                    "trace_id": trace_id,
                    "evidence_mode": mode,
                    "spans": get_trace_spans(trace_id),
                },
            )

    def _set_allure_metadata(self, case: EvalCase) -> None:
        allure.dynamic.title(case.title)
        allure.dynamic.description(self._allure_description(case))
        allure.dynamic.severity(self._severity_label(case.severity))
        allure.dynamic.parameter("case", f"{case.id}: {case.title}")

    def _allure_description(self, case: EvalCase) -> str:
        expected_value = case.expected_value or "No value should be extracted"
        expected_citation = case.expected_citation_text or "No citation should be returned"
        return (
            "**What this case checks**\n\n"
            f"{case.expected_behavior}\n\n"
            "**Expected outcome**\n\n"
            "- Field: Lease Expiration Date\n"
            f"- Result: {case.expected_outcome_label}\n"
            f"- Expected value: {expected_value}\n"
            f"- Expected supporting text: {expected_citation}\n\n"
            "**Why this matters**\n\n"
            f"{case.notes}\n\n"
            "**Quality signals reviewed**\n\n"
            "- Schema validity\n"
            "- Normalized value correctness\n"
            "- Citation presence and support\n"
            "- Null handling where relevant\n"
            "- Confidence range\n"
            "- Mock judge rubric for grounding, reasoning, ambiguity, and hallucination risk"
        )

    def _human_readable_summary(self, case: EvalCase, result: CaseEvaluationResult) -> str:
        status = "PASSED" if result.passed else "FAILED"
        lines = [
            f"Case: {case.title}",
            f"Status: {status}",
            f"Expected behavior: {case.expected_behavior}",
            f"Actual extracted value: {result.extraction.value or 'null'}",
            f"Confidence: {result.extraction.confidence}",
            f"Total score: {result.total_score}",
            f"Runtime: {result.duration_ms} ms",
            "",
            "Deterministic checks:",
        ]
        for metric in result.rule_metrics:
            metric_status = "PASSED" if metric.passed else "FAILED"
            lines.append(f"- {metric.display_name}: {metric_status}. {metric.reason}")

        judge_status = "PASSED" if result.judge.passed else "FAILED"
        lines.extend(
            [
                "",
                "Mock judge rubric:",
                f"- Overall: {judge_status}. {result.judge.reason}",
                f"- Groundedness: {result.judge.groundedness}",
                f"- Reasoning quality: {result.judge.reasoning_quality}",
                f"- Ambiguity handling: {result.judge.ambiguity_handling}",
                f"- Hallucination risk: {result.judge.hallucination_risk}",
            ]
        )
        if result.failed_critical_metrics:
            lines.extend(["", "Critical failures:", *[f"- {name}" for name in result.failed_critical_metrics]])
        return "\n".join(lines)

    def _severity_label(self, raw: str) -> str:
        mapping = {
            "blocker": allure.severity_level.BLOCKER,
            "critical": allure.severity_level.CRITICAL,
            "normal": allure.severity_level.NORMAL,
            "minor": allure.severity_level.MINOR,
            "trivial": allure.severity_level.TRIVIAL,
        }
        return mapping.get(raw.lower(), allure.severity_level.NORMAL)
