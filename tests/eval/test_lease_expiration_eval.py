"""Parametrized quality gate for lease-expiration Data Field extraction."""

import pytest

from eval_harness.models import CaseEvaluationResult, EvalCase
from eval_harness.runner import LeaseExpirationEvalRunner


@pytest.mark.eval
def test_lease_expiration_expects_expected_behavior(
    case: EvalCase,
    lease_expiration_eval_runner: LeaseExpirationEvalRunner,
    evaluation_results: list[CaseEvaluationResult],
) -> None:
    result = lease_expiration_eval_runner.run_case(case)
    evaluation_results.append(result)
    lease_expiration_eval_runner.assert_quality_gate_passed(result)
