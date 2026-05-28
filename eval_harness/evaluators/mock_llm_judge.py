"""Rubric-based local mock judge; no external LLM call is made."""

from rapidfuzz import fuzz

from eval_harness.date_utils import normalize_date
from eval_harness.models import EvalCase, ExtractionResult, JudgeResult
from eval_harness.tracing import get_tracer


class MockLLMJudge:
    """Simulates LLM-as-judge behavior with transparent local rubric rules."""

    # Scores one extraction with the local mock judge rubric.
    def score(self, case: EvalCase, extraction: ExtractionResult) -> JudgeResult:
        with get_tracer().start_as_current_span("score.mock_llm_judge") as span:
            groundedness = self._groundedness(case, extraction)
            reasoning_quality = self._reasoning_quality(case, extraction)
            ambiguity_handling = self._ambiguity_handling(case, extraction)
            hallucination_risk = self._hallucination_risk(case, extraction)
            score = round(
                (groundedness + reasoning_quality + ambiguity_handling + (1.0 - hallucination_risk)) / 4,
                3,
            )
            span.set_attribute("case.id", case.id)
            span.set_attribute("judge.score", score)
            return JudgeResult(
                score=score,
                passed=score >= 0.75,
                reason=(
                    "Local rubric score from groundedness, reasoning quality, ambiguity handling, "
                    "and inverse hallucination risk."
                ),
                groundedness=groundedness,
                reasoning_quality=reasoning_quality,
                ambiguity_handling=ambiguity_handling,
                hallucination_risk=hallucination_risk,
            )

    # Rates whether the answer is supported by the expected citation and value.
    def _groundedness(self, case: EvalCase, extraction: ExtractionResult) -> float:
        if case.expected_value is None:
            return 1.0 if extraction.value is None else 0.0
        if not extraction.citations:
            return 0.0
        expected_citation = case.expected_citation_text or ""
        best_similarity = max(fuzz.token_set_ratio(expected_citation, citation) for citation in extraction.citations)
        value_match = normalize_date(case.expected_value) == normalize_date(extraction.value)
        if best_similarity >= 90 and value_match:
            return 1.0
        if best_similarity >= 75 and value_match:
            return 0.8
        return 0.3

    # Rates whether the reasoning explains the expected case-specific behavior.
    def _reasoning_quality(self, case: EvalCase, extraction: ExtractionResult) -> float:
        reasoning = extraction.reasoning.strip().lower()
        if len(reasoning) < 20:
            return 0.3
        special_terms = ["amendment", "override", "conflicting", "ignored", "no reliable", "not a lease"]
        if any(term in case.expected_behavior.lower() for term in special_terms):
            return 1.0 if any(term in reasoning for term in special_terms) else 0.7
        return 0.9

    # Rates how well ambiguous, missing, or irrelevant evidence is handled.
    def _ambiguity_handling(self, case: EvalCase, extraction: ExtractionResult) -> float:
        behavior = case.expected_behavior.lower()
        reasoning = extraction.reasoning.lower()
        if any(term in behavior for term in ["conflict", "override", "do not use", "missing", "irrelevant"]):
            if any(term in reasoning for term in ["conflicting", "override", "ignored", "does not", "no reliable"]):
                return 1.0
            return 0.5
        return 0.85

    # Rates the risk that the extraction invented an unsupported answer.
    def _hallucination_risk(self, case: EvalCase, extraction: ExtractionResult) -> float:
        if case.expected_value is None:
            return 0.0 if extraction.value is None else 1.0
        expected = normalize_date(case.expected_value)
        actual = normalize_date(extraction.value)
        if expected == actual and extraction.citations:
            return 0.05
        if actual is None:
            return 0.6
        return 0.9
