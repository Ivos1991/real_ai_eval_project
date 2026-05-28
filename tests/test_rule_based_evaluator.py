"""Focused tests for deterministic lease-expiration metrics."""

from assertpy import assert_that
import pytest

from eval_harness.evaluators.rule_based import RuleBasedEvaluator
from eval_harness.models import EvalCase, ExtractionResult


@pytest.mark.unit
def test_rule_based_evaluator_expects_all_metrics_to_pass_for_grounded_match() -> None:
    case = EvalCase(
        id="unit_grounded_match",
        title="Grounded match",
        severity="normal",
        document_text="The Lease Expiration Date is December 31, 2030.",
        expected_value="2030-12-31",
        expected_citation_text="The Lease Expiration Date is December 31, 2030.",
        expected_outcome_label="the correct expiration date",
        expected_outcome_slug="correct_expiration_date",
        expected_behavior="Extract the expected date with supporting citation.",
        notes="Unit fixture.",
    )
    extraction = ExtractionResult(
        value="December 31, 2030",
        confidence=0.95,
        citations=["The Lease Expiration Date is December 31, 2030."],
        reasoning="The cited lease clause states the expiration date.",
    )

    metrics = RuleBasedEvaluator().score(case, extraction)

    assert_that([metric.display_name for metric in metrics if not metric.passed]).described_as(
        "failed deterministic metric labels"
    ).is_empty()


@pytest.mark.unit
def test_rule_based_evaluator_expects_null_case_to_fail_when_value_is_invented() -> None:
    case = EvalCase(
        id="unit_null_case",
        title="Missing expiration date",
        severity="critical",
        document_text="The agreement is month-to-month with no stated expiration date.",
        expected_value=None,
        expected_citation_text=None,
        expected_outcome_label="a null extraction",
        expected_outcome_slug="null_extraction",
        expected_behavior="Return null when no fixed expiration date exists.",
        notes="Unit fixture.",
    )
    extraction = ExtractionResult(
        value="2030-12-31",
        confidence=0.9,
        citations=["The agreement starts on January 1, 2030."],
        reasoning="Guessed an end date.",
    )

    metrics = RuleBasedEvaluator().score(case, extraction)
    failed_metric_names = {metric.name for metric in metrics if not metric.passed}

    assert_that(failed_metric_names).described_as("failed deterministic metric names").contains(
        "exact_or_normalized_value_match",
        "expected_null_handling",
    )
