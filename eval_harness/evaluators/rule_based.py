"""Deterministic lease-expiration extraction metrics."""

from pydantic import ValidationError
from rapidfuzz import fuzz

from eval_harness.date_utils import normalize_date
from eval_harness.models import EvalCase, ExtractionResult, RuleMetricResult
from eval_harness.tracing import get_tracer


class RuleBasedEvaluator:
    METRIC_LABELS = {
        "schema_validity": "Output matches the required schema",
        "exact_or_normalized_value_match": "Extracted date matches the expected date",
        "citation_present": "Citation is present when needed",
        "citation_supports_answer": "Citation supports the extracted answer",
        "expected_null_handling": "Missing values are handled correctly",
        "confidence_range_valid": "Confidence is within the valid range",
    }

    def __init__(self, citation_similarity_threshold: float = 80.0) -> None:
        self._citation_similarity_threshold = citation_similarity_threshold

    def score(self, case: EvalCase, extraction: ExtractionResult) -> list[RuleMetricResult]:
        with get_tracer().start_as_current_span("score.rule_based") as span:
            metrics = [
                self._schema_validity(extraction),
                self._value_match(case, extraction),
                self._citation_present(case, extraction),
                self._citation_supports_answer(case, extraction),
                self._expected_null_handling(case, extraction),
                self._confidence_range_valid(extraction),
            ]
            span.set_attribute("case.id", case.id)
            span.set_attribute("rule_metrics.passed", sum(metric.passed for metric in metrics))
            return metrics

    def _schema_validity(self, extraction: ExtractionResult) -> RuleMetricResult:
        try:
            ExtractionResult.model_validate(extraction.model_dump())
            return self._metric("schema_validity", passed=True, score=1.0, reason="Output matches schema.")
        except ValidationError as error:
            return self._metric(
                name="schema_validity",
                passed=False,
                score=0.0,
                reason=f"Output schema validation failed: {error}",
            )

    def _value_match(self, case: EvalCase, extraction: ExtractionResult) -> RuleMetricResult:
        expected = normalize_date(case.expected_value)
        actual = normalize_date(extraction.value)
        passed = expected == actual
        return self._metric(
            name="exact_or_normalized_value_match",
            passed=passed,
            score=1.0 if passed else 0.0,
            reason=f"Expected normalized value {expected!r}; got {actual!r}.",
        )

    def _citation_present(self, case: EvalCase, extraction: ExtractionResult) -> RuleMetricResult:
        if case.expected_value is None:
            passed = len(extraction.citations) == 0
            reason = "Expected no citation for a null extraction."
        else:
            passed = len(extraction.citations) > 0
            reason = "Expected at least one citation for a non-null extraction."
        return self._metric(name="citation_present", passed=passed, score=1.0 if passed else 0.0, reason=reason)

    def _citation_supports_answer(self, case: EvalCase, extraction: ExtractionResult) -> RuleMetricResult:
        if case.expected_value is None:
            passed = extraction.value is None
            return self._metric(
                name="citation_supports_answer",
                passed=passed,
                score=1.0 if passed else 0.0,
                reason="Null extraction should not invent citation support.",
            )

        expected_citation = case.expected_citation_text or ""
        best_similarity = max((fuzz.token_set_ratio(expected_citation, citation) for citation in extraction.citations), default=0)
        expected_value = normalize_date(case.expected_value)
        actual_value = normalize_date(extraction.value)
        value_matches = expected_value == actual_value
        passed = best_similarity >= self._citation_similarity_threshold and value_matches
        return self._metric(
            name="citation_supports_answer",
            passed=passed,
            score=1.0 if passed else 0.0,
            reason=(
                f"Best citation similarity={best_similarity:.1f}; "
                f"threshold={self._citation_similarity_threshold:.1f}; value_matches={value_matches}."
            ),
        )

    def _expected_null_handling(self, case: EvalCase, extraction: ExtractionResult) -> RuleMetricResult:
        if case.expected_value is not None:
            return self._metric(
                name="expected_null_handling",
                passed=True,
                score=1.0,
                reason="Case expects a concrete value.",
                critical=False,
            )

        passed = extraction.value is None and extraction.confidence <= 0.4 and not extraction.citations
        return self._metric(
            name="expected_null_handling",
            passed=passed,
            score=1.0 if passed else 0.0,
            reason="Null cases require null value, low confidence, and no fabricated citation.",
        )

    def _confidence_range_valid(self, extraction: ExtractionResult) -> RuleMetricResult:
        passed = 0.0 <= extraction.confidence <= 1.0
        return self._metric(
            name="confidence_range_valid",
            passed=passed,
            score=1.0 if passed else 0.0,
            reason=f"Confidence={extraction.confidence}.",
        )

    def _metric(
        self,
        name: str,
        passed: bool,
        score: float,
        reason: str,
        critical: bool = True,
    ) -> RuleMetricResult:
        return RuleMetricResult(
            name=name,
            display_name=self.METRIC_LABELS[name],
            passed=passed,
            score=score,
            reason=reason,
            critical=critical,
        )
