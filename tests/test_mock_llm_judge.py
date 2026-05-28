"""Focused tests for the local rubric-based mock judge."""

import pytest
from assertpy import assert_that

from eval_harness.evaluators.mock_llm_judge import MockLLMJudge
from eval_harness.models import EvalCase, ExtractionResult


@pytest.mark.unit
def test_mock_llm_judge_expects_pass_for_grounded_reasoned_answer() -> None:
    case = EvalCase(
        id="unit_judge_grounded",
        title="Clear lease expiration date",
        severity="normal",
        document_text="The Lease Expiration Date is December 31, 2030.",
        expected_value="2030-12-31",
        expected_citation_text="The Lease Expiration Date is December 31, 2030.",
        expected_outcome_label="the correct expiration date",
        expected_outcome_slug="correct_expiration_date",
        expected_behavior="Extract the clear stated lease expiration date.",
        notes="Unit fixture.",
    )
    extraction = ExtractionResult(
        value="2030-12-31",
        confidence=0.95,
        citations=["The Lease Expiration Date is December 31, 2030."],
        reasoning="The cited lease clause states the expiration date.",
    )

    judge = MockLLMJudge().score(case, extraction)

    assert_that(judge.passed).described_as("mock judge pass status").is_true()
    assert_that(judge.score).described_as("mock judge total score").is_greater_than_or_equal_to(0.75)


@pytest.mark.unit
def test_mock_llm_judge_expects_fail_when_null_case_hallucinates_value() -> None:
    case = EvalCase(
        id="unit_judge_null",
        title="Missing expiration date",
        severity="critical",
        document_text="The agreement is month-to-month with no stated expiration date.",
        expected_value=None,
        expected_citation_text=None,
        expected_outcome_label="a null extraction",
        expected_outcome_slug="null_extraction",
        expected_behavior="Return null with low confidence when no fixed expiration date exists.",
        notes="Unit fixture.",
    )
    extraction = ExtractionResult(
        value="2030-12-31",
        confidence=0.9,
        citations=["The agreement starts on January 1, 2030."],
        reasoning="Guessed an end date.",
    )

    judge = MockLLMJudge().score(case, extraction)

    assert_that(judge.passed).described_as("mock judge pass status").is_false()
    assert_that(judge.hallucination_risk).described_as("hallucination risk score").is_equal_to(1.0)
